# Backup Manager

Another backup script, because nothing else I could find did quite what I wanted.


## Features

* Python based; runs on Windows and Linux
* YAML based configuration == nice and readable
* Can backup from MS SQL, ~~MySQL~~ (coming soon!) or local files
* Backs up to an S3 (or S3-compatible) bucket (because fuck FTP)
* Compresses backups using 7-zip (LZMA compression algorithm)
* Hourly, daily, weekly and monthly backups
* Sensible file names (ISO 8601 for the win)
* Can run compression threads as low priority (Windows only)
* Password protected archives (AES-256)
* Handles deletion of old backups
* Multiple backup schedules per resource (eg. 10 daily backups + 4 weekly backups + 6 monthly backups, etc)
* Sensible deduplication of overlapping periods (eg. a single backup can belong to multiple period "sets")
* Most recent backup always stored at a static path (not date based)


## Important Notes and Warnings

This tool works for me but may well not work for anyone else. Testing has been limited to the environments I use, specifically Windows Server 2003, 2008 R2 and Ubuntu 14.04 LTS.

Expect to get your hands dirty, use at your own risk, etc, etc.


## Setup Overview

To get this working you'll need to get a few things in place. The broad strokes are...

1. Install the prerequisites
2. Get a copy of the code
3. Create your config.yaml
4. Setup a S3 bucket and IAM credentials (or equivilant)
5. Schedule the script to run (in Cron or Windows Task Scheduler)

These steps are detailed below.


## Prerequisites

### Windows

1. [Python 2.7](https://www.python.org/downloads) (32 bit)
2. [Pip](http://pip.readthedocs.org/en/latest/installing.html)
3. [7-zip](http://www.7-zip.org/download.html) -- Either the full version or just the CLI
4. [PyWin32](http://sourceforge.net/projects/pywin32/files/pywin32/Build%20219/pywin32-219.win32-py2.7.exe/download) (optional, Windows only) -- Used to low-priority the 7z processes

### Linux

Basically the same as above but without the PyWin32 library.

Use your package manager of choice. For me (Ubuntu 14.0.4 LTS) this is:

> sudo apt-get install python python-pip p7zip-full

### MS SQL Support

For this you need:

* sqlcmd -- Comes with MS SQL Server
* The [SQL Server Maintenance Solution](http://ola.hallengren.com) scripts by Ola Hallengren -- Apply them to the master db


## Get the code

Easiest way is to grab it from git. If I've made this project public (which otherwise, how are you reading this..?) it should be as easy as:

> git clone git@github.com:molomby/mol-backup-manager.git


## Create your config.yml

The config structure is largely documented in the example configs provided; either `config-example-win.yaml` or `config-example-linux.yaml` depending on your platform.

These configs are equivilant other than the sample paths given.

Create a copy of the relevant example named config.yaml and populate it with your details.


## AWS Config

You'll need to have a bucked ready to accept your backups... 


//	* Create S3 bucket
//		.. eg: conetix-bluetree-backups

	* Create an IAM users
		Eg.. "backups-auto-sesat.molomby.com"

	* Create credentials at AWS for S3 access
		Eg.. "backups-auto-sesat.molomby.com"
		{
		 "Statement": [
		   {
		     "Action": "s3:*",
		     "Effect": "Allow",
		     "Resource": "arn:aws:s3:::molomby-backups/auto/sesat.molomby.com/*"
		   },
		   {
		     "Action": ["s3:ListAllMyBuckets", "s3:GetBucketLocation"],
		     "Effect": "Allow",
		     "Resource": "arn:aws:s3:::*"
		   },
		   {
		     "Action": "s3:ListBucket",
		     "Effect": "Allow",
		     "Resource": "arn:aws:s3:::molomby-backups"
		   }
		 ]
		}


	* Update config.yaml
		.. All the things
		.. Test


Creating scheduled task (Windows)
	.. "Auto DB backups"

	* Task Scheduler > New task..
		.. C:\Server\backup-manager\run.py
		
		* "Run whether logged in or not" (as Molomby)
		* Triggers > Add trigger..
			* One time (whenever)
			* Repeat task ever 1 hour, indefinitely


.. If creating a specific MS SQL user, they must have the sysadmin server role
.. See.. http://stackoverflow.com/questions/10366676/backup-permissions
