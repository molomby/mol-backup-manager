#!/usr/bin/python
from __future__ import print_function
from bunch import Bunch

import os.path, copy, smtplib, sys, traceback, datetime

from modules.resource import Resource
from modules.local import LocalFiles, LocalMsSqlDb, LocalMySqlDb


def main():
	error_count = 0

	# Catching errors in the config won't do us much good as we've nowhere to log or email them
	config = load_config()
	defaults = config["defaults"]

	# Start logging
	log_filepath = os.path.join(config["log-dir"], "backup-manager-" + str(datetime.datetime.now().hour) + ".log")
	tee = Tee(log_filepath)

	# verify we can connect to the SMTP server
	# If this doesn't work we want to continue but warn the user
	try:
		print("Verifying mail server credentials.. ")
		email = config["email"]
		smtp = smtplib.SMTP(email["server"], email["port"])
		smtp.set_debuglevel(False)
		smtp.login(email["user"], email["password"])
	except Exception:
		error_count =+ 1
		print("\n\nERROR encountered:\n", traceback.format_exc(), "\n\n")
	

	# Process each resource
	for resource_key in config["resources"]:
		tee.flush()
		try:
			rc = Bunch(copy.deepcopy(config["resources"][resource_key]))

			# Create our local system object that handles local files, db connections, etc
			if "path" in rc:
				locsys = LocalFiles(config["7zip-execPath"], rc.path, rc.limit if "limit" in rc else None)
			elif "mssql" in rc:
				mssql = Bunch(rc.mssql)
				locsys = LocalMsSqlDb(config["7zip-execPath"], config["mssql-backup-dir"], config["log-dir"], mssql.server, mssql.database, mssql.user, mssql.password, mssql.type)
			elif "mysql" in rc:
				mysql = Bunch(rc.mysql)
				locsys = LocalMySqlDb(config["7zip-execPath"], config["mysql-backup-dir"], config["log-dir"], mysql.server, mysql.database, mysql.user, mysql.password)
			else:
				print("Invalid resource config; must contain one of: path, mssql, mysql.")
				print(rc)			
			
			# Get the resource arguments and apply defaults
			args = dict(filter(lambda i:i[0] in ("schedule","store","password","compression"), rc.iteritems()))
			args = copy.deepcopy(dict(defaults.items() + args.items()))

			print("\nProcessing resource:", resource_key)
			resource = Resource(resource_key, locsys, **args)
			resource.process()

		except Exception:
			error_count =+ 1
			print("\n\nERROR encountered while processing resource:", resource_key, "\n", traceback.format_exc(), "\n\n")

	if error_count > 0:
		tee.flush()
		tee.close()
		email_output(log_filepath, smtp, email["from_email"], email["to_email"], email["subject"])

	print("Done; exiting.")


def load_config():
	from yaml import load

	print("Loading config...")
	path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.yaml")
	return load(open(path))


def email_output(log_filepath, smtp, from_email, to_email, subject):
	import socket, time, string
	
	print("\n\nSending error report email...\n")

	email_args = {
		"log_text": open(log_filepath, "r").read(),
		"from_email": from_email,
		"to_email": to_email,
		"subject": subject,
		"server_name": socket.gethostname(),
		"server_tz": time.tzname[0],
		"current_datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	}

	template = string.Template("""From: "Automated Backups" <$from_email>
To: "Administrator" <$to_email>
Subject: $subject

Server Name:	$server_name
Date/time:		$current_datetime ($server_tz)

An error was encounted while backing up one or more resources. 
What follows is the output generated while attempting to gather, compress and copy/upload the configured resources.

-------------------

$log_text
""")
	message = template.substitute(**email_args)

	#print(message)
	smtp.sendmail(from_email, to_email, message)
	
	

# Lets us maps output (though print()) to a file and the standard output
class Tee(object):
	def __init__(self, name):
		self.file = open(name, 'w')
		self.stdout = sys.stdout
		sys.stdout = self

	def close(self):
		if self.stdout is not None:
			sys.stdout = self.stdout
			self.stdout = None
		if self.file is not None:
			self.file.close()
			self.file = None

	def write(self, data):
		self.file.write(data)
		self.stdout.write(data)

	def flush(self):
		self.file.flush()
		self.stdout.flush()

	def __del__(self):
		self.close()



if __name__ == '__main__':
    main()
