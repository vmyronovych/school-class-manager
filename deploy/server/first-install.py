#!/usr/bin/python3
"""Bootstrap the dedicated school DC from an extracted and verified release."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('site', type=Path)
args = parser.parse_args()
site = json.loads(args.site.read_text())
fields = {'realm', 'domain', 'address', 'lan_interface', 'dns_forwarder'}
if set(site) != fields or any(not isinstance(v, str) or not v for v in site.values()):
    parser.error('Expected the five nonempty fields from site.example.json.')
if os.geteuid() or socket.gethostname() != 'school-server':
    parser.error('Run on the dedicated school-server VM as root.')
if Path('/var/lib/samba/private/sam.ldb').exists():
    parser.error('Domain already exists. Use install-panel.sh for application upgrades.')
root = Path(__file__).resolve().parent
subprocess.run(['sha256sum', '--quiet', '-c', 'SHA256SUMS'], cwd=root.parent, check=True)
arch = subprocess.check_output(['dpkg','--print-architecture'],text=True).strip()
if arch != (root.parent / 'architecture').read_text().strip():
    parser.error('Release architecture does not match this VM.')
ipaddress.IPv4Address(site['address'])
ipaddress.IPv4Address(site['dns_forwarder'])
subprocess.run(['bash', root / 'install-samba.sh'], check=True)
command = ['python3', root / 'provision-samba.py']
for key, value in site.items():
    command.extend(('--' + key.replace('_', '-'), value))
subprocess.run(command, check=True)
subprocess.run(['python3', root / 'set-admin-password.py'], check=True)
subprocess.run(['bash', root / 'install-panel.sh'], check=True)
