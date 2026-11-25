#!/usr/bin/env bash
# Restore complete cold state into EMPTY storage on a separate isolated VM.
set -euo pipefail
umask 077
test "$(id -u)" = 0
test "$#" = 2 || { echo 'Usage: restore.sh BACKUP_DIR RESTORE_EXISTING_DOMAIN'; exit 1; }
test "$2" = RESTORE_EXISTING_DOMAIN
backup="$(realpath "$1")"
test -f "$backup/COMPLETE"
test -f "$backup/state.tar"
mountpoint -q /srv/classroom
exec 9>/run/classroom-backup.lock
flock -n 9
test ! -e /srv/classroom/domain
test ! -e /srv/classroom/domain-ready
test ! -e /srv/classroom/restore-in-progress
test -z "$(find /srv/classroom/homes -mindepth 1 -print -quit)"
(cd "$backup"; sha256sum -c SHA256SUMS)
# Require exact installed package versions for a cold TDB/LDB restoration.
dpkg-query -W > /run/classroom-packages.lock
cmp "$backup/packages.lock" /run/classroom-packages.lock || { echo 'Package versions differ; rebuild matching guest before restore'; exit 1; }
python3 - "$backup" <<'PY'
import json, pathlib, sys, tarfile
b = pathlib.Path(sys.argv[1])
c = json.loads(pathlib.Path('/etc/classroom/config.json').read_text())
old = json.loads((b / 'config.json').read_text())
assert c['mode'] in ('lab', 'recovery'), 'Restore must remain isolated; reconnect only after validation'
for key in ('realm', 'domain', 'hostname', 'ip', 'netmask'):
    assert c[key] == old[key], f'Restore requires original {key}'
with tarfile.open(b / 'state.tar') as tar:
    members = tar.getmembers()
    for m in members:
        name = pathlib.PurePosixPath(m.name)
        assert not name.is_absolute() and '..' not in name.parts, 'Unsafe archive member'
        if m.issym() or m.islnk():
            # Generated Samba config links point inside the fixed persistent root.
            link = pathlib.PurePosixPath(m.linkname)
            assert '..' not in link.parts
            assert not link.is_absolute() or str(link).startswith('/srv/classroom/'), 'Unsafe link'
    assert any(m.name.endswith('/domain/private/sam.ldb') for m in members), 'Domain database missing'
PY
systemctl stop samba-ad-dc
touch /srv/classroom/restore-in-progress
tar --acls --xattrs --xattrs-include='*' --numeric-owner -xpf "$backup/state.tar" -C /srv/classroom
# Retain isolated mode in identity until planned cutover. Never provision a new SID.
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('/srv/classroom/identity.json')
c = json.loads(pathlib.Path('/etc/classroom/config.json').read_text())
v = json.loads(p.read_text()); v['mode'] = c['mode']; p.write_text(json.dumps(v, indent=2)+'\n')
PY
test -f /srv/classroom/domain/private/sam.ldb
test -f /srv/classroom/domain-ready
rm /srv/classroom/restore-in-progress
python3 /usr/local/lib/classroom/setup.py
systemctl unmask samba-ad-dc
systemctl enable --now samba-ad-dc
samba-tool dbcheck --cross-ncs
samba-tool ntacl sysvolcheck
echo 'Existing domain restored. Validate accounts, SID, file ACLs, and Windows trust before cutover.'
