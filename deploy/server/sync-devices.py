#!/usr/bin/python3 -I
"""Publish one read-only report credential per enabled computer in the deployment group."""
import fcntl
import grp
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile
from samba import ldb
from samba.auth import system_session
from samba.param import LoadParm
from samba.samdb import SamDB

root = Path('/var/lib/scm-enrollment')
os.umask(0o077)
lock = open('/run/scm-enrollment.lock', 'a')
fcntl.flock(lock, fcntl.LOCK_EX)
lp = LoadParm()
lp.load_default()
db = SamDB(url='/var/lib/samba/private/sam.ldb', session_info=system_session(), lp=lp)
group, = db.search(expression='(&(objectClass=group)(sAMAccountName=scm-agent-computers))', attrs=['member'])
gid = grp.getgrnam('scm').gr_gid
active = set()
for dn in group.get('member', []):
    row, = db.search(base=str(dn), scope=ldb.SCOPE_BASE, attrs=['objectClass','sAMAccountName','userAccountControl','objectSid'])
    if b'computer' not in row['objectClass'] or int(str(row['userAccountControl'])) & 2:
        continue
    name = str(row['sAMAccountName']).upper()
    if not re.fullmatch(r'[A-Z0-9](?:[A-Z0-9-]{0,13}[A-Z0-9])?\$', name):
        continue
    sid = db.schema_format_value('objectSid', row['objectSid'][0]).decode()
    # A rejoined computer with the same name and a new SID receives a new key.
    path = root / (name[:-1] + '.key')
    active.add(path)
    uid = int(subprocess.check_output(['wbinfo', '--sid-to-uid', sid], text=True))
    if uid == 0:
        raise RuntimeError('Refusing a privileged Unix identity')
    if path.exists() and os.getxattr(path, 'user.scm.sid').decode() == sid:
        continue
    with tempfile.NamedTemporaryFile(dir=root, delete=False) as output:
        tmp = Path(output.name)
        output.write(secrets.token_hex(24).upper().encode())
    try:
        os.chown(tmp, 0, gid)
        tmp.chmod(0o440)
        subprocess.run(['setfacl', '-m', f'u:{uid}:r--', tmp], check=True)
        os.setxattr(tmp, 'user.scm.sid', sid.encode())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
for path in root.glob('*.key'):
    if path not in active:
        path.unlink()
