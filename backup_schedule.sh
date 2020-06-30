#!/bin/bash
python3 $(dirname $(readlink -f "$0"))/backup_schedule.py /home/www-backup 1.2.4.8.24
