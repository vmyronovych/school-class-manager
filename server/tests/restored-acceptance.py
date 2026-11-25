#!/usr/bin/python3
"""Authenticate original test users after full cold restoration, preserving SID/files."""
import json, os, pathlib, subprocess, tempfile
from samba.samdb import SamDB
from samba.param import LoadParm
from samba.auth import system_session

assert os.geteuid() == 0
c = json.loads(pathlib.Path('/etc/classroom/config.json').read_text())
assert c['mode'] == 'lab' and c['realm'].endswith('.TEST')
saved = json.loads(pathlib.Path('/srv/classroom/etc/lab-test-credentials.json').read_text())
lp = LoadParm(); lp.load('/etc/samba/smb.conf')
db = SamDB(url=lp.private_path('sam.ldb'), session_info=system_session(), lp=lp)
assert str(db.get_domain_sid()) == saved['sid'], 'Domain identity changed'
with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    for index, (user, password) in enumerate(saved['accounts']):
        auth = tmp / 'auth'; auth.write_text(f'username = {user}\npassword = {password}\ndomain = {c["domain"]}\n'); auth.chmod(0o600)
        def smb(command):
            return subprocess.run(['smbclient', '//'+c['ip']+'/pupils', '-A', str(auth), '-c', command], text=True, capture_output=True)
        download = tmp / 'download'
        r = smb(f'get {user}/marker.txt {download}')
        assert r.returncode == 0 and download.read_text() == 'private-marker-'+user
        peer = saved['accounts'][1-index][0]
        r = smb(f'get {peer}/marker.txt {tmp / "forbidden"}')
        assert 'NT_STATUS_ACCESS_DENIED' in r.stdout+r.stderr
        payload = tmp / 'payload'; payload.write_text('forbidden')
        r = smb(f'put {payload} {peer}/intrusion.txt')
        assert 'NT_STATUS_ACCESS_DENIED' in r.stdout+r.stderr
print('PASS: original SID, original passwords, private files, and cross-user denials survived restoration')
