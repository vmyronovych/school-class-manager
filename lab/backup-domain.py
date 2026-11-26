#!/usr/bin/env python3
"""Bundle a native Samba domain backup, pupil files and host configuration for this lab."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import socket
import subprocess
import tempfile
import uuid

from samba import ldb
from samba.auth import system_session
from samba.param import LoadParm
from samba.samdb import SamDB


def run(*args):
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode:
        # Keep tool diagnostics private; never put domain secrets in chat/log output.
        raise RuntimeError(f'{args[0]} failed (exit {result.returncode}); inspect locally.')
    return result.stdout


def main():
    if os.geteuid() != 0 or socket.gethostname() != 'school-server':
        raise SystemExit('Run as root inside the school-server lab VM.')
    os.umask(0o077)
    lp = LoadParm(); lp.load_default()
    if lp.get('realm') != 'SCHOOL.TEST':
        raise SystemExit('Expected SCHOOL.TEST.')
    db = SamDB(url='/var/lib/samba/private/sam.ldb', session_info=system_session(), lp=lp)
    attrs = ['objectSid', 'sAMAccountName', 'homeDrive', 'homeDirectory',
             'userAccountControl', 'primaryGroupID']
    inventory = {'domain_sid': db.get_domain_sid(), 'users': {}, 'unix_ids': {}}
    for name in ['student1', 'student2', 'DESKTOP-N8KR882$']:
        row = db.search(expression='(sAMAccountName=' + ldb.binary_encode(name) + ')', attrs=attrs)[0]
        inventory['users'][name] = {
            key: [db.schema_format_value(key, value).decode() for value in row[key]]
            for key in attrs if key in row}
    for name in ['student1', 'student2']:
        account = pwd.getpwnam('SCHOOL\\' + name)
        inventory['unix_ids'][name] = [account.pw_uid, account.pw_gid]
    inventory['samba_version'] = run('samba', '--version').strip()
    inventory['packages'] = run('dpkg-query', '-W', 'samba', 'samba-ad-dc', 'python3-samba')
    inventory['created_utc'] = datetime.now(timezone.utc).isoformat()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    destination = Path('/home/ubuntu') / f'school-domain-{stamp}-{uuid.uuid4().hex[:12]}.tar.gz'
    homes = None
    try:
        with tempfile.TemporaryDirectory(prefix='scm-domain-backup-') as stage:
            root = Path(stage)
            domain = root / 'domain'; domain.mkdir()
            run('samba-tool', 'dbcheck', '--cross-ncs')
            run('samba-tool', 'domain', 'backup', 'offline', '--targetdir=' + str(domain))
            archives = list(domain.glob('*.tar.bz2'))
            if len(archives) != 1:
                raise RuntimeError('Expected one native domain archive.')
            archives[0].rename(root / 'domain.tar.bz2'); domain.rmdir()
            output = run('/usr/local/sbin/scm-backup-student-homes', 'backup')
            homes = Path(next(line.removeprefix('ARCHIVE=') for line in output.splitlines()
                              if line.startswith('ARCHIVE=')))
            shutil.move(homes, root / 'homes.tar.gz')
            config = root / 'host-config'; config.mkdir()
            for source in ['/etc/samba/smb.conf', '/etc/krb5.conf', '/etc/nsswitch.conf',
                           '/etc/hosts', '/etc/resolv.conf', '/etc/netplan',
                           '/etc/cloud/cloud.cfg.d/99-school-hosts.cfg',
                           '/etc/cloud/templates/hosts.debian.tmpl']:
                path = Path(source)
                target = config / path.relative_to('/')
                target.parent.mkdir(parents=True, exist_ok=True)
                if path.is_dir():
                    shutil.copytree(path, target)
                else:
                    shutil.copy2(path, target)
            (root / 'inventory.json').write_text(json.dumps(inventory, indent=2))
            run('tar', '-czf', str(destination), '-C', stage, '.')
        destination.chmod(0o600)
        user = pwd.getpwnam('ubuntu')
        os.chown(destination, user.pw_uid, user.pw_gid)
        with destination.open('rb') as file:
            checksum = hashlib.file_digest(file, 'sha256').hexdigest()
        print('DOMAIN_BUNDLE=' + str(destination))
        print('SHA256=' + checksum)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        if homes is not None:
            homes.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
