#!/usr/bin/python
from __future__ import print_function

import datetime


class Schedule(object):

	# Does the "most recent, non-latest" backup cover all our current periods? (that are in use)
	@staticmethod
	def calculate_period_indexes(date):
		# This is basically arbitary but we mesure from 2001-01-01 because its also the start of a year, a month AND a week
		basedate = datetime.datetime(2001, 1, 1)
		now_delta = date - basedate

		return {
			"hour": (now_delta.days * 24) + date.hour, 
			"day": now_delta.days, 
			"week": int(now_delta.days / 7) + 1, 
			"month": ((date.year - basedate.year) * 12) + (date.month - basedate.month)
		}

	@staticmethod
	def calculate_periods(date):
		return Schedule.convert_indexes_to_periods(Schedule.calculate_period_indexes(date))

	@staticmethod
	def convert_indexes_to_periods(idxs):
		ps = set()
		if "hour" in idxs: ps.add("h"+str(idxs["hour"]))
		if "day" in idxs: ps.add("d"+str(idxs["day"]))
		if "week" in idxs: ps.add("w"+str(idxs["week"]))
		if "month" in idxs: ps.add("m"+str(idxs["month"]))
		return ps


	def __init__(self, hourly, daily, weekly, monthly):

		initlocs = locals()
		for arg in ["hourly","daily","weekly","monthly"]:
			if not isinstance(initlocs[arg], int):
				raise TypeError("Schedule config value '" + str(arg) + "' must be an integer.")

		self.hourly = hourly
		self.daily = daily
		self.weekly = weekly
		self.monthly = monthly

		# Get the (numeric) period indexes for the current date
		now_indexes = self.calculate_period_indexes(datetime.datetime.now())
		
		# Build list for each period type and combine them into a single set
		self.periods = frozenset(
			set(["h" + str(i) for i in range(now_indexes["hour"], now_indexes["hour"] - self.hourly, -1)]) |
			set(["d" + str(i) for i in range(now_indexes["day"], now_indexes["day"] - self.daily, -1)]) |
			set(["w" + str(i) for i in range(now_indexes["week"], now_indexes["week"] - self.weekly, -1)]) |
			set(["m" + str(i) for i in range(now_indexes["month"], now_indexes["month"] - self.monthly, -1)])
		)

		# What are the current periods that are in use (ie.. configs > 0)
		if self.hourly <= 0: now_indexes.pop("hour")
		if self.daily <= 0: now_indexes.pop("day")
		if self.weekly <= 0: now_indexes.pop("week")
		if self.monthly <= 0: now_indexes.pop("month")
		
		self.now_periods = frozenset(self.convert_indexes_to_periods(now_indexes))


	# Are there any backups that don't "hit" our configured periods?
	def identify_extranious(self, backups):
		periods = set(self.periods)
		extranious = set()

		print("  Checking for extranious backups, expecting:", self.periods)
		
		# loop through the backups (always sorted by date ascending)
		for b in backups:
			bps = self.calculate_periods(b.date)
			hits = periods & bps
			if not any(hits): extranious.add(b)		# If none of this backups periods intersect with the schedule, it's extranious
			periods = periods - (hits)					# Remove schedule periods covered by this backup
			print("    *", b.date, bps, ".. needed by:", hits)
			
		print("  Found", str(len(extranious)), "..", [e.filename for e in extranious], "extranious backups")

		return extranious

	def is_uptodate(self, backups):
		mrnl_backup = backups[-1]	# Most recent non-latest
		mrnl_periods = Schedule.calculate_periods(mrnl_backup.date)
		
		return not any(self.now_periods - mrnl_periods)
