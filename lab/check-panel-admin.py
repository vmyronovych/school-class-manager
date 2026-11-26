#!/usr/bin/env python3
"""Read-only regression check for mixed-case Administrator sessions on the lab DC."""
import json
import os
import subprocess

from samba.auth import system_session
from samba.param import LoadParm
from samba.samdb import SamDB

assert os.geteuid() == 0, 'Run on the Ubuntu DC with sudo'
lp = LoadParm()
lp.load_default()
db = SamDB(url='/var/lib/samba/private/sam.ldb', session_info=system_session(), lp=lp)
row = db.search(expression='(sAMAccountName=Administrator)', attrs=['objectSid', 'sAMAccountName'])[0]
actor_sid = db.schema_format_value('objectSid', row['objectSid'][0]).decode()

def call(operation, login, sid=actor_sid):
    result = subprocess.run(['/usr/local/sbin/scm-directory'],
                            input=json.dumps({'op': operation, 'actor': {'login': login, 'sid': sid}}),
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout)

# Include the directory spelling returned at sign-in and already-issued cookies.
for login in dict.fromkeys([str(row['sAMAccountName'][0]), 'administrator', 'ADMINISTRATOR']):
    result = call('list', login)
    assert 'data' in result, f'{login} list failed: {result}'
    assert {'student1', 'student2'} <= {p['login'] for p in result['data']}, 'Pupils missing'
    session = call('session', login)
    assert session['data']['login'] == 'administrator', 'Session login is not canonical'
    assert session['data']['role'] == 'Admin'
    assert call('list', login, actor_sid + '-1') == {'error': 'forbidden'}, 'SID check bypassed'
print('ADMIN_SESSION_OK: directory/mixed-case names, pupil list, canonical login, SID enforcement')
