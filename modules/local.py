#!/usr/bin/python
from __future__ import print_function

import tempfile, subprocess, os.path, time, glob, sys


class LocalBase(object):
	def __init__(self, exec_path):
		self.exec_path = exec_path
		self.temps = []

	def identify_files(self):
		raise NotImplemented("Should be subclassed")

	def create_archive(self, files, password=None, compression=5):
		# create a temporary file for the subprocess output
		archivePath = os.path.join(tempfile.mkdtemp(), "current.7z")
		print("  Adding to archive at", archivePath)
		
		
		# Add each file in sequence
		for f in files:

			# Build and run the command to compress the file
			command = '"'+self.exec_path+'" a -t7z "'+archivePath+'" "'+f+'" -mx='+str(compression)+' -mmt=2'
			if password != None: command += ' -p'+password

			# Command contains passwords.. don't print/log
			#print("    *", f, "to archive with command:\n      ", command )
			print("    *", f, "to archive" )
			subproc = subprocess.Popen(command, shell=True) #, stdout=subprocess.PIPE
			self.reduce_process_priority(subproc.pid)

			poll_interval = 0.05
			while subproc.returncode is None:
				#print(".", subproc.returncode, end='')
				time.sleep(poll_interval)
				poll_interval = min(1, poll_interval * 1.2)
				subproc.poll()
			print("  Add operation complete")
			
			
			# TODO: Log/output filesize
			
			# out, err = subproc.communicate()
			# print(out)
			
		self.temps.append(archivePath)
		return archivePath

	# An attempt at a cross-platform reduction in subprocess priority
	def reduce_process_priority(self, process_id):
		if sys.platform == "win32":
			# Needs pywin32... http://sourceforge.net/projects/pywin32/files/pywin32/
			try: 
				import win32api, win32process, win32con
				handle = win32api.OpenProcess( win32con.PROCESS_ALL_ACCESS, True, process_id )
				win32process.SetPriorityClass( handle, win32process.BELOW_NORMAL_PRIORITY_CLASS )
			except Exception, e:
				print("\n  Failed to set subprocess priority:", e)
		else:
			import psutil
			psutil.Process(process_id).set_nice(15)

	def clean_up(self):
		print("  Cleaning up..")
		for t in self.temps:
			print("    * Deleting ", t)
			os.remove(t)


class LocalFiles(LocalBase):
	def __init__(self, exec_path, path, limit=None):
		super(LocalFiles, self).__init__(exec_path)
		self.path = path
		self.limit = limit

	def identify_files(self):
		if self.limit == None:
			files = glob.glob(self.path)
		elif self.limit == "latest":
			all_files = glob.iglob(self.path)
			files = [max(all_files, key=os.path.getctime)] if any(all_files) else []
		else:
			raise NotImplementedError("The '" + str(self.limit) + "' limit has not been implemented")

		print("  Idenfied", len(files), "file(s)")
		return files


class LocalMsSqlDb(LocalBase):
	def __init__(self, exec_path, backup_dir, log_dir, server, database, user, password, type):
		super(LocalMsSqlDb, self).__init__(exec_path)
		self.backup_dir = backup_dir
		self.log_dir = log_dir

		self.server = server
		self.database = database
		self.user = user
		self.password = password
		self.type = type

	def identify_files(self):
		import datetime, string

		log_file = os.path.join(self.log_dir, "sqlcmd-" + self.database + "-" + self.type + "-" + datetime.datetime.now().strftime('%Y%m%d') + ".log")

		sql_subs = {"db_name": self.database, "dir_path": self.backup_dir, "backup_type": self.type}
		sql_temp = "EXECUTE dbo.DatabaseBackup @Databases='$db_name', @Directory='$dir_path', @BackupType='$backup_type', @Compress='N', @Encrypt='N', @CleanupTime=25"
		sql = string.Template(sql_temp).substitute(**sql_subs)

		cmd_subs = {"server": self.server, "user": self.user, "password": self.password, "log_file": log_file, "sql": sql}
		cmd_temp = 'sqlcmd -S $server -U $user -P $password -d master -Q "$sql" -b -o "$log_file"'
		cmd = string.Template(cmd_temp).substitute(**cmd_subs)

		# Command contains passwords.. don't print/log
		#print("  Creating MSSQL backup with command:\n    ", cmd, "\n  Executing", end="")
		print("  Creating MSSQL backup\n  Executing", end="")
		subproc = subprocess.Popen(cmd) #, stdout=subprocess.PIPE

		poll_interval = 0.05
		while subproc.returncode is None:
			print(".", end='')
			time.sleep(poll_interval)
			poll_interval = min(1, poll_interval * 1.2)
			subproc.poll()

		print(" Done")

		#output = open(log_file).read()
		#print("  Logfile\n---------------------", output)

		# Finding the actual files
		server_dir = LocalMsSqlDb.server_name_to_dir(self.server)
		file_mask = os.path.join(self.backup_dir, server_dir, self.database, self.type, server_dir+"_"+self.database+"_"+self.type+"_20[0-9][0-9][0-1][0-9][0-3][0-9]_[0-2][0-9][0-5][0-9][0-5][0-9].bak")
		print("  Looking for files..", file_mask)

		# TODO: Log/output filesize

		files = [max(glob.iglob(file_mask), key=os.path.getctime)]
		print("  Idenfied", len(files), "file(s)")
		return files


	# TODO: Fix issues around this.. path uses server-reported name rather than given in config?
	@staticmethod
	def server_name_to_dir(s):
		i = s.split("\\")
		if len(i) == 1: return i[0].upper()
		p = i[0].split(",")
		return p[0].upper() + "$" + i[1]


class LocalMySqlDb(LocalBase):
	def __init__(self, exec_path, backup_dir, log_dir, server, database, user, password):
		super(LocalMySqlDb, self).__init__(exec_path)
		self.backup_dir = backup_dir
		self.log_dir = log_dir

		self.server = server
		self.database = database
		self.user = user
		self.password = password

	def identify_files(self):
		import datetime, string

		log_file = os.path.join(self.log_dir, self.database + "-" + str(datetime.datetime.now().hour) + ".log")
		backup_file = os.path.join(self.backup_dir, self.database + ".sql")
		
		# mysqldump -u root -p[root_password] [database_name] > dumpfilename.sql 2> output.log
		cmd_subs = {"server": self.server, "user": self.user, "password": self.password, "log_file": log_file, "database": self.database, "backup_file": backup_file}
		cmd_temp = "mysqldump -u $user -v -p$password $database > '$backup_file' 2> '$log_file'"
		
		cmd = string.Template(cmd_temp).substitute(**cmd_subs)

		print("RUNNING: ", cmd)
		
		
		# Command contains passwords.. don't print/log
		print("  Creating MySQL backup\n  Executing", end="")
		subproc = subprocess.Popen(cmd, shell=True)		# , stdout=subprocess.PIPE

		poll_interval = 0.05
		while subproc.returncode is None:
			print(".", end='')
			time.sleep(poll_interval)
			poll_interval = min(1, poll_interval * 1.2)
			subproc.poll()

		print(" Done")

		#output = open(log_file).read()
		#print("  Logfile\n---------------------", output)

		# Finding the actual files
		files = [max(glob.iglob(backup_file), key=os.path.getctime)]
		print("  Idenfied", len(files), "file(s)")

		return files
