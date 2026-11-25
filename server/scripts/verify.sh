#!/usr/bin/env bash
set -euo pipefail
mountpoint -q /srv/classroom
test -f /srv/classroom/domain-ready
systemctl is-active --quiet samba-ad-dc
testparm -s >/dev/null
samba-tool dbcheck --cross-ncs
samba-tool ntacl sysvolcheck
python3 - <<'PY'
import json, subprocess
c = json.load(open('/etc/classroom/config.json'))
for record in (f"_ldap._tcp.{c['realm'].lower()}", f"_kerberos._udp.{c['realm'].lower()}"):
    text = subprocess.check_output(['dig', '@'+c['ip'], record, 'SRV', '+short'], text=True)
    assert c['hostname']+'.' in text, f'Missing SRV: {record}'
print('DNS SRV records present')
PY
ss -lntup
echo 'Check Samba does not listen on NAT address; complete Windows/privacy tests before rollout.'
