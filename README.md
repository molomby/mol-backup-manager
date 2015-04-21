# Backup Manager

Another backup script; because nothing I could find did quite what I wanted.



## Features

* Python based; runs on Windows and Linux
* YAML based configuration == nice and readable
* Can backup directly from MS SQL, MySQL or local files
* Backs up to an S3 (or S3-compatible) bucket (because fuck FTP)
* Compresses backups using 7-zip (LZMA compression algorithm)
* Hourly, daily, weekly and monthly backups
* Sensible file names (ISO 8601 for the win)
* Runs compression threads as low priority
* Password protected archives (AES-256)
* Notifies by email if/when errors are encountered
* Multiple backup schedules per resource (eg. 10 daily backups + 4 weekly backups + 6 monthly backups, etc)
* Sensible deduplication of overlapping periods (eg. a single backup can belong to multiple period "sets")
* Most recent backup always stored at a static path (not date based)



## Important Notes and Warnings

This tool works for me but may well not work for anyone else. Testing has been limited to the environments I use, specifically Windows Server 2003, 2008 R2 and Ubuntu 14.04 LTS.

Expect to get your hands dirty, use at your own risk, YMMV, etc.

Specific things to look out for:

* LZMA is fairly memory hungry so watch out for that
* Not a lot of configuration options at this stage (eg. can't disable compression, encryption, emails, etc)
* Basically assumes MySQL is Linux only
* Will not function without a working mail server (!)
* The last 24 hours of logs are stored locally as is the most recent backup for each resource


# Setup

To get this working you'll need to get a few things in place:

1. Install the prerequisites
2. Get the code
3. Setup a S3 bucket and IAM credentials (or equivilant)
4. Create your config.yaml
5. Test everything runs as it should
6. Schedule the script to run (in Cron or Windows Task Scheduler)

These steps are detailed below.



## 1. Prerequisites

### Windows

1. [Python 2.7](https://www.python.org/downloads) (32 bit)
2. [Pip](http://pip.readthedocs.org/en/latest/installing.html)
3. [7-zip](http://www.7-zip.org/download.html) -- Either the full version or just the CLI
4. [PyWin32](http://sourceforge.net/projects/pywin32/files/pywin32/Build%20219/pywin32-219.win32-py2.7.exe/download) (optional, Windows only) -- Used to low-priority the 7z processes

#### MS SQL Support

For this you need:

* sqlcmd -- Comes with MS SQL Server
* The [SQL Server Maintenance Solution](http://ola.hallengren.com) scripts by Ola Hallengren -- Apply them to the master db

If you're creating a specific MS SQL user that will be used to perform the backups (generall a good idea), they [may need the `sysadmin` server role](http://stackoverflow.com/questions/10366676/backup-permissions).

### Linux

Basically the same as above but without the PyWin32 library.

Use your package manager of choice. For me (Ubuntu 14.0.4 LTS) this is:

	sudo apt-get install python python-dev python-pip p7zip-full


## 2. Get the code

Easiest way is to grab it from git. If I've made this project public (which otherwise, how are you reading this..?) it should be as easy as:

	git clone git@github.com:molomby/mol-backup-manager.git

You should then be able to install using pip and the requirements.txt file:
	
	cd mol-backup-manager
	pip install -r requirements.txt



## 3. AWS Config

Backups are stored on [S3](http://aws.amazon.com/s3/), one of the many fantastic AWS services.

You'll need to have a S3 bucked ready to accept your backups and a credentials for an IAM user with appropriate access. These should be added to your config.yaml file as described in the next section.

As a starting point, this policy will restrict an IAM user to a specific directory within a bucket while still providing access necessary for the backup script to function.

	{
		"Statement": [
			{
				"Action": "s3:*",
				"Effect": "Allow",
				"Resource": "arn:aws:s3:::molomby-backups/auto/servername123.molomby.com/*"
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
		],
		"Version": "2012-10-17"
	}

See the [AWS documentation](http://docs.aws.amazon.com/AmazonS3/latest/dev/example-bucket-policies.html) and [AWS blog](http://blogs.aws.amazon.com/security/post/Tx1P2T3LFXXCNB5/Writing-IAM-policies-Grant-access-to-user-specific-folders-in-an-Amazon-S3-bucke) for details and more policy examples.



## 4. Create your config.yml

The config structure is largely documented in the example configs provided; either `config-example-win.yaml` or `config-example-linux.yaml` depending on your platform. Create a copy of the relevant example named config.yaml and populate it with your details.

### Email

These backup scripts *require* a working email server to run and will fail without one.

I suggest the most excellent [Mandrill](https://mandrillapp.com) service from MailChimp. They provide very reliable mail delivery infrastructure, free up to 12k mails a month.

### YAML is pretty sweet

The 'defaults' structure in config.yaml is handy but don't forget you can use other YAML features, eg. referential anchors.



## 5. Testing

At this point (if you're following these steps in order) you should have a working backup script but it's a good idea to test everything's working before continuing to the last step. Execute run `run.py` and check the output.

The process will work though each resource, comparing the files stored remotely with the configured schedules. If a resource is missing it's current backup for any period it will be backed up, compressing and uploaded to S3. Any errors encountered will generate an email containing the output of the script.

If the process completes successfully you'll see:

	Resource processing complete.
	Done; exiting.



## 6. Scheduling the backups

The backup script should be run every hour for the `hourly` period to function. If none of your resources are scheduled for `hourly` backups it's still probably a good idea execute the script hourly in case backup frequency is later increased.

The scheduling process itself is platform dependant.

### Windows

In Windows the built in task scheduler will do the job. When configuring the task, ensure the following options are set correctly:

* "Run whether logged in or not" 
* Run as a user with sufficient access to the filesystem to perform the backups
* When configuring the triggers (Triggers > Add trigger > .. )
** "One time" (anytime in the past is fine)
** Repeat task ever 1 hour, indefinitely

### Linux

On Linux, `cron` is the weapon of choice. If you haven't already, add a line to your crontab, or `root`s if you'd rather. 

In my case it looks like this:

	# Run the backup process every hour
	0 * * * * python /home/ubuntu/mol-backup-manager/run.py auto

