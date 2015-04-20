#!/usr/bin/python
from __future__ import print_function

from stores import StoreFactory
from schedule import Schedule


class Resource(object):

	# Resource(resource_key, locsys, **args)
	def __init__(self, key, locsys, schedule, store, password=None, compression=5):
		self.key = key
		self.locsys = locsys
		
		self.schedule = Schedule(**schedule)
		self.store = StoreFactory(key, store)

		self.password = password
		self.compression = compression


	def process(self):

		# List current backups
		backups = self.store.list_backups()
		latest = self.store.get_latest_backup()

		print("  Found", len(backups), "backups")
		print("  Latest exists?", "Yes" if latest != None else "No")

		# Identify extranious; delete them
		for e in self.schedule.identify_extranious(backups):
			self.store.remove_backup(e)
		
		# TODO: Compare local latest md5 with remote version before upload
		
		# New backup required? (missing most recent?); get from source
		if latest == None or not self.schedule.is_uptodate(backups):
			files = self.locsys.identify_files()
			archive_path = self.locsys.create_archive(files, self.password, self.compression)
			self.store.add_latest(archive_path)
			self.locsys.clean_up()

		else:
			print("  Backups up-to-date; no action required")

		print("  Resource processing complete.")