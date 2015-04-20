#!/usr/bin/python
from __future__ import print_function
import os
from datetime import datetime


class S3Progress(object):
	def __init__(self, local_path, indent=6, bar_width=50):
		self.started = False
		self.filesize = os.path.getsize(local_path)
		self.num_cb = int(self.filesize / (1024 * 1024)) # Once for each x Kb
		self.indent = (" " * indent)
		self.bar_width = bar_width


	def start(self):
		print(self.indent + "Starting...", end='')

	def cb_function(self, complete, total):
		if not self.started:
			self.started = True
			self.startTime = datetime.now()

		comp = int((complete * 1.0 / total) * (self.bar_width - 3))
		incomp = (self.bar_width - 3) - comp
		
		perc = int(complete * 100 / total)
		elapsed = (datetime.now() - self.startTime).total_seconds()
		self.avgKbs = "{:,.2f}".format((complete / 1024) / elapsed) if elapsed > 0 else "--.--"
		
		print(self.indent + "[" + ("="*comp) + ">" + ("-"*incomp) + "] " + str(perc)  +  "% at " + self.avgKbs + " KB/s", end="\r")

	def final(self):
		print(self.indent + "[" + ("="*(self.bar_width-2)) + "] 100% at " + self.avgKbs + " KB/s     ") # trailing space intentional

