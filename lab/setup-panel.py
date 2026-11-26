#!/usr/bin/env python3
"""Prepare groups and the per-user share without changing existing pupils or passwords."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
from samba import ldb
from samba.auth import system_session
from samba.param import LoadParm
from samba.samdb import SamDB

if os.geteuid()!=0 or socket.gethostname()!='school-server':
    raise SystemExit('Run as root only on school-server.')
os.umask(0o077)
lp=LoadParm();lp.load_default()
if lp.get('realm')!='SCHOOL.TEST':
    raise SystemExit('Expected SCHOOL.TEST.')
db=SamDB(url='/var/lib/samba/private/sam.ldb',session_info=system_session(),lp=lp)
for group in ['scm-students','vchyteli']:
    if not db.search(expression=f'(sAMAccountName={group})',attrs=[]):
        db.newgroup(group)
group=db.search(expression='(sAMAccountName=scm-students)',attrs=['member'])[0]
existing={str(value).casefold() for value in group.get('member',[])}
for login in ['student1','student2']:
    rows=db.search(expression='(sAMAccountName='+ldb.binary_encode(login)+')',attrs=[])
    if len(rows)!=1:raise SystemExit('Expected existing lab pupil: '+login)
    if str(rows[0].dn).casefold() not in existing:
        db.add_remove_group_members('scm-students',[login],add_members_operation=True)
state=Path('/var/lib/scm-directory');state.mkdir(mode=0o700,exist_ok=True)
state.chmod(0o700)
config=Path('/etc/samba/smb.conf')
original=config.read_text()
marker='# SCM PANEL PUPILS'
if marker not in original:
    if '[pupils]' in original:
        raise SystemExit('Existing unmanaged pupils share; inspect before proceeding.')
    added='''
# SCM PANEL PUPILS
[pupils]
    csc policy = disable
    path = /srv/school/home/%U
    valid users = @scm-students
    read only = no
    browseable = no
    guest ok = no
    create mask = 0600
    directory mask = 0700
    force create mode = 0600
    force directory mode = 0700
    acl_xattr:ignore system acls = no
'''
    with tempfile.NamedTemporaryFile(mode='w',dir=config.parent,delete=False) as file:
        candidate=Path(file.name);file.write(original+added)
    try:
        subprocess.run(['testparm','-s',str(candidate)],capture_output=True,check=True)
        backup=config.with_name('smb.conf.before-panel')
        if not backup.exists():shutil.copy2(config,backup)
        candidate.chmod(0o644);os.replace(candidate,config)
        subprocess.run(['smbcontrol','all','reload-config'],check=True)
    finally:candidate.unlink(missing_ok=True)
print('PANEL_GROUPS_AND_PRIVATE_SHARE_READY')
