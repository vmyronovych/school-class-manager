#!/usr/bin/python3
"""Run as root on isolated lab DC. Creates exactly two disposable pupil accounts.
No secret is printed/passed in argv. Refuses a production or existing test account.
"""
import json, os, pathlib, secrets, subprocess, tempfile
from samba.samdb import SamDB
from samba.param import LoadParm
from samba.auth import system_session
from samba.dcerpc import security
from samba.ndr import ndr_unpack

assert os.geteuid() == 0
c = json.loads(pathlib.Path('/etc/classroom/config.json').read_text())
assert c['mode'] == 'lab' and c['realm'].endswith('.TEST'), 'Isolated lab only'
lp = LoadParm(); lp.load('/etc/samba/smb.conf')
db = SamDB(url=lp.private_path('sam.ldb'), session_info=system_session(), lp=lp)
sid = str(db.get_domain_sid())
accounts = ['labalice', 'labbob']
credentials = []
for user in accounts:
    assert not db.search(base=db.domain_dn(), expression=f'(sAMAccountName={user})'), 'Use a fresh lab or existing-account verification drill'
    password = secrets.token_urlsafe(24) + '!aA1'
    home = f"\\\\{c['hostname']}.{c['realm'].lower()}\\pupils\\{user}"
    db.newuser(user, password, homedrive='H:', homedirectory=home)
    db.add_remove_group_members('Pupils', [user], add_members_operation=True)
    entry = db.search(base=db.domain_dn(), expression=f'(sAMAccountName={user})', attrs=['objectSid'])[0]
    usid = str(ndr_unpack(security.dom_sid, bytes(entry['objectSid'][0])))
    folder = pathlib.Path('/srv/classroom/homes') / user
    folder.mkdir(mode=0o700)
    sddl = f'O:SYG:SYD:P(A;OICI;0x1301bf;;;{usid})(A;OICI;FA;;;{sid}-512)(A;OICI;FA;;;SY)'
    subprocess.run(['samba-tool', 'ntacl', 'set', sddl, str(folder), '--use-s3fs', '--service=pupils'], check=True)
    credentials.append((user, password))

def check_pair(creds, restore=False):
    with tempfile.TemporaryDirectory(prefix='classroom-test-') as tmp:
        tmp = pathlib.Path(tmp)
        for index, (user, password) in enumerate(creds):
            auth = tmp / 'auth'; auth.write_text(f'username = {user}\npassword = {password}\ndomain = {c["domain"]}\n'); auth.chmod(0o600)
            payload = tmp / 'payload'; payload.write_text('private-marker-'+user)
            def smb(command):
                return subprocess.run(['smbclient', '//'+c['ip']+'/pupils', '-A', str(auth), '-c', command], text=True, capture_output=True)
            if not restore:
                r = smb(f'put {payload} {user}/marker.txt')
                assert r.returncode == 0, r.stdout+r.stderr
            download = tmp / 'download'
            r = smb(f'get {user}/marker.txt {download}')
            assert r.returncode == 0 and download.read_text() == 'private-marker-'+user, r.stdout+r.stderr
            peer = accounts[1-index]
            r = smb(f'get {peer}/marker.txt {tmp / "forbidden"}')
            assert 'NT_STATUS_ACCESS_DENIED' in r.stdout+r.stderr and not (tmp/'forbidden').exists(), 'Peer folder was accessible'
            r = smb(f'put {payload} {peer}/intrusion.txt')
            assert 'NT_STATUS_ACCESS_DENIED' in r.stdout+r.stderr, 'Peer folder was writable'
            assert not (pathlib.Path('/srv/classroom/homes')/peer/'intrusion.txt').exists()
    print('PASS: both accounts read/write own files; both peer read/write attempts denied')

check_pair(credentials)
# Credentials needed to verify the SAME accounts after isolated restore; root-only.
path = pathlib.Path('/srv/classroom/etc/lab-test-credentials.json')
path.write_text(json.dumps({'sid': sid, 'accounts': credentials})); path.chmod(0o600)
print('Root-only lab credentials saved for restoration drill. Reset interactively before Windows login; never export this file to Git.')
