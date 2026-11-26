#!/usr/bin/env python3
"""Verify GPO/SMB access with disposable users; Windows application is a separate check."""
import configparser
import json
import os
from pathlib import Path
import pwd
import secrets
import shutil
import socket
import subprocess
import tempfile
import time

from samba.auth import system_session, user_session, AUTH_SESSION_INFO_DEFAULT_GROUPS, AUTH_SESSION_INFO_AUTHENTICATED
from samba.dcerpc import security
from samba.ndr import ndr_unpack
from samba.param import LoadParm
from samba.samdb import SamDB

assert os.geteuid() == 0 and socket.gethostname() == 'school-server'
os.umask(0o077)
lp = LoadParm(); lp.load_default()
db = SamDB(url='/var/lib/samba/private/sam.ldb', session_info=system_session(), lp=lp)
state = json.loads(Path('/var/lib/scm-directory/folder-redirection/policy.json').read_text())
policy_file = Path(state['path'])
raw = policy_file.read_bytes()
ini = configparser.ConfigParser(interpolation=None); ini.read_string(raw.decode('utf-16'))
assert dict(ini['Version']) == {'version': '100'}
assert len(ini['Folder_Redirection']) == 2
for guid, folder in [('{FDD39AD0-238F-46AF-ADB4-6C85480369C7}', 'Documents'),
                     ('{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}', 'Desktop')]:
    assert ini['Folder_Redirection'][guid] == state['groupSid'] + ';'
    rule = ini[guid + '_' + state['groupSid']]
    assert rule['Flags'] == '1001'
    assert rule['FullPath'] == state['unc'] + '\\' + folder
for share in ['pupils', 'student1', 'student2']:
    assert lp.get('csc policy', share) == 'disable', 'Offline caching still enabled'
subprocess.run(['samba-tool', 'ntacl', 'sysvolcheck'], check=True)
gpo = db.search(expression='(cn=' + state['guid'] + ')', attrs=['nTSecurityDescriptor'])[0]
sddl = ndr_unpack(security.descriptor, gpo['nTSecurityDescriptor'][0]).as_sddl(security.dom_sid(db.get_domain_sid()))
apply_prefix = '(OA;CI;CR;edacfd8f-ffb3-11d1-b41d-00a0c968f939;;'
assert apply_prefix + state['groupSid'] + ')' in sddl, 'Pupil Apply Group Policy permission missing'
assert apply_prefix + 'AU)' not in sddl, 'Apply Group Policy granted to all authenticated users'

token = secrets.token_hex(4)
student, control = 'frpupil' + token, 'frcontrol' + token
password = 'Aa1!' + secrets.token_urlsafe(24)
created = []
home = Path('/srv/school/home') / student
try:
    db.newuser(student, password); created.append(student)
    db.add_remove_group_members('scm-students', [student], add_members_operation=True)
    db.newuser(control, 'Aa1!' + secrets.token_urlsafe(24)); created.append(control)
    for account, expected in [(student, True), (control, False)]:
        row = db.search(expression='(sAMAccountName=' + account + ')', attrs=[])[0]
        session = user_session(db, lp_ctx=lp, dn=str(row.dn), session_info_flags=AUTH_SESSION_INFO_DEFAULT_GROUPS | AUTH_SESSION_INFO_AUTHENTICATED)
        # samba-tool gpo list checks Read, not Apply Group Policy. Verify the
        # group SID used by both the Apply ACE and MS-GPFR mapping in the token.
        assert (state['groupSid'] in {str(sid) for sid in session.security_token.sids}) == expected, 'Folder-redirection group token mismatch'
    for attempt in range(10):
        try:
            identity = pwd.getpwnam('SCHOOL\\' + student); break
        except KeyError:
            if attempt == 9: raise
            time.sleep(0.2)
    home.mkdir(mode=0o700); os.chown(home, identity.pw_uid, identity.pw_gid)
    with tempfile.TemporaryDirectory(prefix='scm-fr-check-') as temporary:
        root = Path(temporary)
        auth = root / 'auth'; auth.write_text(f'username = {student}\npassword = {password}\ndomain = SCHOOL\n')
        remote = 'school.test/Policies/' + state['guid'] + '/User/Documents & Settings/fdeploy1.ini'
        downloaded = root / 'fdeploy1.ini'
        fetched = subprocess.run(['smbclient', '//school-server.school.test/sysvol', '-A', str(auth),
                                  '-c', f'get "{remote}" {downloaded}'], capture_output=True)
        assert fetched.returncode == 0 and downloaded.read_bytes() == raw, 'Pupil cannot read exact policy over SMB'
        source = root / 'probe.txt'; source.write_text('Disposable folder redirection probe\n')
        for folder in ['Documents', 'Desktop']:
            returned = root / (folder + '.txt')
            command = f'mkdir {folder}; put {source} {folder}/probe.txt; get {folder}/probe.txt {returned}; del {folder}/probe.txt; rmdir {folder}'
            result = subprocess.run(['smbclient', '//school-server.school.test/pupils', '-A', str(auth), '-c', command], capture_output=True)
            assert result.returncode == 0 and returned.read_bytes() == source.read_bytes(), 'Private redirected folder roundtrip failed'
        denied = subprocess.run(['smbclient', '//school-server.school.test/student1', '-A', str(auth), '-c', 'ls'], capture_output=True)
        assert denied.returncode != 0 and b'NT_STATUS_ACCESS_DENIED' in denied.stdout + denied.stderr, 'Peer share not denied'
    print('FOLDER_REDIRECTION_SERVER_OK: native policy, pupil-only filtering, SYSVOL ACL/read, private Documents/Desktop SMB, caching disabled, peer denial.')
    print('WINDOWS_APPLICATION_PENDING: verify known-folder paths after pupil sign-out/sign-in.')
finally:
    for account in reversed(created): db.deleteuser(account)
    if home.exists(): shutil.rmtree(home)
    print('DISPOSABLE_REDIRECTION_ACCOUNTS_REMOVED')
