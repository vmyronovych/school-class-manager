#!/usr/bin/python3
"""Explicit topology transition only; never rename/readdress the domain."""
import json, os, pathlib, subprocess
assert os.geteuid() == 0
p = pathlib.Path('/srv/classroom/identity.json')
c = json.loads(pathlib.Path('/etc/classroom/config.json').read_text())
v = json.loads(p.read_text())
for key in ('realm', 'domain', 'hostname', 'ip', 'netmask'):
    assert c[key] == v[key], 'Identity/address change requires separately reviewed migration'
assert c['mode'] in ('recovery', 'lan')
if c['mode'] == 'lan':
    assert c['confirmed'] is True
expected = f"TOPOLOGY {v['mode']} TO {c['mode']} {c['realm']}"
assert input(f'Original DC must be OFF; backup must exist. Type {expected}: ') == expected
subprocess.run(['systemctl', 'stop', 'samba-ad-dc'], check=True)
v['mode'] = c['mode']; p.write_text(json.dumps(v, indent=2)+'\n')
print('Mode changed. Rerun provisioning with approved topology. No domain data altered.')
