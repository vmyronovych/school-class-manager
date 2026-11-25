#!/usr/bin/python3
"""Interactive creation only: passwords never enter argv, config, or files."""
import getpass, json, logging, os, pathlib, re, subprocess, sys

ROOT = pathlib.Path('/srv/classroom')

def main():
    assert os.geteuid() == 0, 'Run with sudo'
    assert sys.argv[1:] == ['create'], 'Usage: domain.py create'
    c = json.loads(pathlib.Path('/etc/classroom/config.json').read_text())
    assert subprocess.run(['mountpoint', '-q', str(ROOT)]).returncode == 0
    target = ROOT / 'domain'
    assert not target.exists() and not (ROOT / 'domain-ready').exists(), 'Existing/partial domain: use recovery, never reprovision'
    assert c['mode'] in ('lab', 'lan'), 'Recovery mode must restore, never create a domain'
    assert c['mode'] == 'lab' or c['confirmed'] is True
    expected = f"CREATE {c['realm']} {c['ip']}"
    assert input(f'Type {expected} to create a NEW, EMPTY domain: ') == expected
    secret = getpass.getpass('New domain Administrator password: ')
    assert len(secret) >= 14, 'Use at least 14 characters'
    assert secret == getpass.getpass('Repeat password: '), 'Passwords differ'
    from samba.provision import provision
    from samba.auth import system_session
    logger = logging.getLogger('classroom-provision')
    logger.addHandler(logging.NullHandler())
    # Existing targetdir is never reused. A failed attempt is deliberately blocked.
    provision(logger, system_session(), targetdir=str(target), realm=c['realm'],
              domain=c['domain'], hostname=c['hostname'], hostip=c['ip'],
              adminpass=secret, serverrole='active directory domain controller',
              dns_backend='SAMBA_INTERNAL', skip_sysvolacl=False)
    del secret
    conf = target / 'etc/smb.conf'
    text = conf.read_text()
    text = re.sub(r'(?im)^\s*dns forwarder\s*=.*$', '', text)
    text = text.replace('[global]', f'''[global]
        interfaces = lo enp0s8
        bind interfaces only = yes
        dns forwarder = {c['dns_forwarder']}
        server min protocol = SMB2
        map to guest = Never
        ntp signd socket directory = /srv/classroom/domain/ntp_signd
''', 1)
    text += '''
[pupils]
        path = /srv/classroom/homes
        read only = no
        browseable = yes
        guest ok = no
        access based share enum = yes
        hide unreadable = yes
        smb encrypt = required
        acl_xattr:ignore system acls = yes
        inherit acls = yes
'''
    (ROOT / 'etc/smb.conf').write_text(text)
    conf.unlink()
    conf.symlink_to(ROOT / 'etc/smb.conf')
    active = pathlib.Path('/etc/samba/smb.conf')
    active.unlink(missing_ok=True)
    active.symlink_to(ROOT / 'etc/smb.conf')
    subprocess.run(['testparm', '-s'], check=True, stdout=subprocess.DEVNULL)
    (ROOT / 'domain-ready').write_text(c['realm'] + '\n')
    subprocess.run(['python3', '/usr/local/lib/classroom/setup.py'], check=True)
    subprocess.run(['systemctl', 'unmask', 'samba-ad-dc'], check=True)
    subprocess.run(['systemctl', 'enable', '--now', 'samba-ad-dc'], check=True)
    for group in ('Pupils', 'Teachers'):
        subprocess.run(['samba-tool', 'group', 'add', group], check=True)
    subprocess.run(['python3', '/usr/local/lib/classroom/accounts.py', 'init-share'], check=True)
    print('Domain created. Record Administrator credential securely; take a baseline backup.')

if __name__ == '__main__':
    main()
