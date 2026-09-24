#!/bin/bash
set -e
rsync -a --delete --exclude='.snapshots' /srv/data/home/  /srv/backup/home/
rsync -a --delete --exclude='.snapshots' /srv/data/class/ /srv/backup/class/
rsync -a --delete /var/lib/scm/ /srv/backup/scm/ 2>/dev/null || true
rsync -a --delete /etc/scm/     /srv/backup/scm-etc/ 2>/dev/null || true
if [ "$(date +%u)" = 7 ]; then
  rm -rf /srv/data/ad-backup/*
  samba-tool domain backup offline --targetdir=/srv/data/ad-backup
  rsync -a --delete /srv/data/ad-backup/ /srv/backup/ad-backup/
fi
