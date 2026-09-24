#!/bin/bash
set -e
ts=$(date -u +@GMT-%Y.%m.%d-%H.%M.%S)
for v in home class; do
  btrfs subvolume snapshot -r /srv/data/$v /srv/data/$v/.snapshots/$ts
  find /srv/data/$v/.snapshots -maxdepth 1 -name '@GMT-*' -mtime +30 \
    -exec btrfs subvolume delete {} \;
done
