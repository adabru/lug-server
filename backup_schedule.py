#!/usr/bin/python

import sys, os, re, datetime

if len(sys.argv) < 3:
  print(
    'usage:\n   \033[1mbackup_schedule.py\033[22m /path/to/backup/folder x.y.z\n\n' +
    'The scheme are the approximate distances between the kept backups.\n' +
    'Files in the backup folder must be in the scheme *yyyymmdd*')
  exit()

backups = {}
p = re.compile(r'[\d]{8}')
for file in os.listdir(sys.argv[1]):
  m = p.search(file)
  if m != None:
    d = datetime.datetime.strptime( m.group(), "%Y%m%d" ).date()
    if not d in backups:
      backups[d] = {
        'files': [],
        'delete': True
      }
    backups[d]['files'].append(file)

periods = [int(x) for x in sys.argv[2].split('.')]

# keep today's backup
today = datetime.date.today()
if today in backups:
  backups[today]['delete'] = False

# find out which other backups to keep
cursor = today
for p in periods:
  cursor -= datetime.timedelta(days=p)
  # find the best suited backup, i.e. the oldest backup that is not older than the specified period
  best = min({k: v for k, v in backups.items() if k >= cursor}, default=None)
  if best != None:
    backups[best]['delete'] = False

# delete obsolete backups
for b in backups:
  if backups[b]['delete']:
    for file in backups[b]['files']:
      os.remove(sys.argv[1] + '/' + file)
