#!/usr/bin/python
from __future__ import print_function

import os.path, posixpath, glob, shutil, datetime, re, ntpath
from boto.s3.connection import S3Connection, Key
from abc import ABCMeta, abstractmethod

from progress import S3Progress


def StoreFactory(resource_key, config):
	typekey = config.pop("type", None);
	if typekey == "s3":
		return StoreS3(resource_key, **config)
	elif typekey == "dir":
		return StoreDir(resource_key, **config)
	else:
		raise Exception("Invalid store type: '" + str(typekey) + "'")


# A class representing a single backed up archive
class Backup(object):
	def __init__(self, filepath):
		self.filepath = filepath
		self.filename = ntpath.basename(filepath)
		
		self.date = None
		
		m = re.search("(20[0-9][0-9])([0-1][0-9])([0-3][0-9])-([0-2][0-9])([0-5][0-9])", self.filename)
		ml = re.search("-latest\.", self.filename)
		
		if ml == None and m != None:
			try:
				self.date = datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)))
			except Exception as e:
				print(e)



class Store(object):
	__metaclass__ = ABCMeta

	def __init__(self, resource_key, path):
		self.path = path
		self.resource_key = resource_key

	@abstractmethod
	def list_backups(self): raise NotImplementedError("Base Store object must be extended.")
	
	@abstractmethod
	def get_latest_backup(self): raise NotImplementedError("Base Store object must be extended.")
	
	@abstractmethod
	def remove_backup(self, backup): raise NotImplementedError("Base Store object must be extended.")
	
	@abstractmethod
	def add_latest(self, archive_path): raise NotImplementedError("Base Store object must be extended.")


class StoreS3(Store):

	def __init__(self, resource_key, path, bucket, accessId, secretKey):
		super(StoreS3, self).__init__(resource_key, path)
		
		# JM 20140602: Having problems with the univeral s3 address so connecting directly to the Sydney region instead
		#self.conn = S3Connection(accessId, secretKey)
		from boto.s3 import connect_to_region
		from boto.s3.connection import Location
		
		self.conn = connect_to_region(Location.APSoutheast2, aws_access_key_id=accessId, aws_secret_access_key=secretKey)

		self.bucket = self.conn.get_bucket(bucket)

		self.backupsPath_regex = posixpath.join(self.path, self.resource_key, self.resource_key + "-20[0-9][0-9][0-1][0-9][0-3][0-9]-[0-2][0-9][0-5][0-9]\.7z")[1:]
		self.latestPath = posixpath.join(self.path, self.resource_key, self.resource_key + "-latest.7z")[1:]
		self.currentPath = posixpath.join(self.path, self.resource_key, self.resource_key + "-" + datetime.datetime.now().strftime("%Y%m%d-%H%M") + ".7z")[1:]

		self.all_files = [f.name.encode('utf-8') for f in self.bucket.list()]


	# Create a list of Backup objects
	def list_backups(self):
		
		# Filter the files in the bucket down to those that match our mask
		backups = []
		for f in self.all_files:
			match = re.match(self.backupsPath_regex, f)
			if match != None and match.group(0) == f:
				backups.append(Backup(f))

		backups.sort(key=lambda x: x.date)
		return backups

	# Return the 'latest' backup
	def get_latest_backup(self):
		return self.latestPath if self.latestPath in self.all_files else None
	
	# Delete the backup specified
	def remove_backup(self, backup):
		self.bucket.delete_key(self.bucket.get_key(backup.filepath))

	# Upload backup as 'latest' and copy to dated filename
	def add_latest(self, archive_path):
		print("  Adding backup from", archive_path)
		
		print("    * Uploading to", self.latestPath)
		pbar = S3Progress(archive_path)
		Key(self.bucket, self.latestPath).set_contents_from_filename(archive_path, cb=pbar.cb_function, num_cb=pbar.num_cb)
		pbar.final()

		#self.bucket.get_key(self.latestPath).set_contents_from_filename(archive_path)
		print("    * Copying to", self.currentPath)
		self.bucket.copy_key(self.currentPath, self.bucket.name, self.latestPath)


# [dirpath]/[object-key]/[object-key]-[YYYYMMDD]-[HHmm].7z
class StoreDir(Store):
	def __init__(self, resource_key, path):
		if not os.path.isdir(path):
			raise Exception("Path provided (" + path + ") isn't a directory or doesn't exist.")

		super(StoreDir, self).__init__(resource_key, path)

		self.backupsPath_globmask = os.path.join(self.path, self.resource_key, self.resource_key + "-20[0-9][0-9][0-1][0-9][0-3][0-9]-[0-2][0-9][0-5][0-9].7z")
		self.latestPath = os.path.join(self.path, self.resource_key, self.resource_key + "-latest.7z")
		self.currentPath = os.path.join(self.path, self.resource_key, self.resource_key + "-" + datetime.datetime.now().strftime("%Y%m%d-%H%M") + ".7z")

	# Create a list of Backup objects
	def list_backups(self):
		files = glob.glob(self.backupsPath_globmask)
		backups = [Backup(f) for f in files]
		backups.sort(key=lambda x: x.date)
		return backups

	# Return the 'latest' backup
	def get_latest_backup(self):
		return self.latestPath if os.path.exists(self.latestPath) else None
		
	# Delete the backup specified
	def remove_backup(self, backup):
		os.remove(backup.filepath)

	# Upload backup as 'latest' and copy to dated filename
	def add_latest(self, archive_path):
		print("  Copying backup from", archive_path, "to...")

		dir_path = os.path.dirname(self.currentPath)
		if not os.path.exists(dir_path): os.makedirs(dir_path)

		print("    *", self.latestPath)
		shutil.copyfile( archive_path, self.latestPath )
		print("    *", self.currentPath)
		shutil.copyfile( archive_path, self.currentPath )


# Register the Store subclass against the abstract base class
Store.register(StoreS3)
Store.register(StoreDir)
