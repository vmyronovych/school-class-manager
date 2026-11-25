#!/usr/bin/env bash
set -euo pipefail
umask 077
test "$(id -u)" = 0
test -f /srv/classroom/domain-ready
mountpoint -q /srv/classroom
exec 9>/run/classroom-backup.lock
flock -n 9 || { echo 'Another backup/restore is running'; exit 1; }
out="${1:-/var/tmp/classroom-backups}"
mkdir -p "$out"
out="$(realpath "$out")"
case "$out" in /srv/classroom|/srv/classroom/*) echo 'Backup must be outside persistent state tree'; exit 1;; esac
chmod 700 "$out"
dest="$out/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 700 "$dest"
systemctl stop samba-ad-dc
trap 'systemctl start samba-ad-dc' EXIT
# Official domain backup supplements the complete same-DC cold archive.
samba-tool domain backup offline --targetdir="$dest"
tar --acls --xattrs --xattrs-include='*' --numeric-owner -cpf "$dest/state.tar" -C /srv/classroom .
cp /etc/classroom/config.json "$dest/config.json"
dpkg-query -W > "$dest/packages.lock"
cp /usr/local/lib/classroom/restore.sh "$dest/restore.sh"
(cd "$dest"; sha256sum ./*.tar ./*.tar.bz2 ./config.json ./packages.lock ./restore.sh > SHA256SUMS)
touch "$dest/COMPLETE"
echo "Backup complete: $dest. Contains password hashes and private files. Export/encrypt now."
