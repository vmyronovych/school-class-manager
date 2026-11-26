#!/usr/bin/env python3
"""Restore drill only in the disposable school-recovery VM, with no external network."""

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import pwd
import secrets
import signal
import socket
import subprocess
import time

from samba import ldb
from samba.auth import system_session
from samba.param import LoadParm
from samba.samdb import SamDB

BASE = Path('/var/lib/scm-recovery')
RESTORED = BASE / 'restored'
CONF = RESTORED / 'etc/smb.conf'
NS = 'scm-recovery'
IP = '192.168.1.176'


def run(args, **kwargs):
    result = subprocess.run(args, capture_output=True, text=True, **kwargs)
    if result.returncode:
        if BASE.exists():
            (BASE / 'command-error.log').write_text(result.stdout + result.stderr)
        raise RuntimeError(f'{args[0]} failed (exit {result.returncode}); inspect private command-error.log.')
    return result.stdout


def inside(args, **kwargs):
    return run(['ip', 'netns', 'exec', NS, *args], **kwargs)


def prepare(archive):
    if BASE.exists():
        raise SystemExit('Recovery directory exists. Inspect it; do not overwrite a previous drill.')
    BASE.mkdir(mode=0o700)
    # Only accept a bundle created by backup-domain.py under your control.
    run(['tar', '-xzf', str(archive), '-C', str(BASE)])
    run(['ip', 'netns', 'add', NS])
    run(['ip', '-n', NS, 'link', 'set', 'lo', 'up'])
    run(['ip', '-n', NS, 'link', 'add', 'dummy0', 'type', 'dummy'])
    run(['ip', '-n', NS, 'addr', 'add', IP + '/24', 'dev', 'dummy0'])
    run(['ip', '-n', NS, 'link', 'set', 'dummy0', 'up'])
    output = inside(['samba-tool', 'domain', 'backup', 'restore',
                     '--backup-file=' + str(BASE / 'domain.tar.bz2'),
                     '--targetdir=' + str(RESTORED), '--newservername=SC-RECOVERY',
                     '--host-ip=' + IP])
    (BASE / 'restore.log').write_text(output)
    print('NATIVE_DOMAIN_RESTORE_OK', flush=True)


def check():
    links = json.loads(run(['ip', '-j', '-n', NS, 'link']))
    if {link['ifname'] for link in links} != {'lo', 'dummy0'}:
        raise RuntimeError('Unexpected recovery network interface; refusing to start Samba.')
    if run(['ip', '-n', NS, 'route', 'show', 'default']).strip():
        raise RuntimeError('Recovery namespace has an external route.')
    inventory = json.loads((BASE / 'inventory.json').read_text())
    if run(['samba', '--version']).strip() != inventory['samba_version']:
        raise RuntimeError('Use the same Samba version as the backup for this drill.')
    config = CONF.read_text().replace('interfaces = lo eth1', 'interfaces = lo dummy0')
    config = config.replace('dns forwarder = 192.168.1.1', 'dns forwarder =')
    if 'dns update command =' not in config:
        config = config.replace('[global]', '[global]\n\tdns update command = /usr/sbin/samba_dnsupdate --use-samba-tool')
    # Own file paths; do not expose or alter the working server's directories.
    config = config.replace('/srv/school/home/', str(BASE / 'files/home') + '/')
    CONF.write_text(config)
    netdir = Path('/etc/netns') / NS
    netdir.mkdir(parents=True, exist_ok=True)
    (netdir / 'resolv.conf').write_text('nameserver 127.0.0.1\nsearch school.test\n')
    (netdir / 'hosts').write_text('127.0.0.1 localhost\n' + IP +
                                ' sc-recovery.school.test sc-recovery\n')
    files = BASE / 'files'
    files.mkdir(exist_ok=True)
    run(['tar', '--acls', '--xattrs', '--xattrs-include=*', '--numeric-owner',
         '--same-owner', '--same-permissions', '-xzf', str(BASE / 'homes.tar.gz'), '-C', str(files)])
    # Compare all file contents and metadata before runtime checks mutate test files.
    spec = importlib.util.spec_from_file_location('homes', '/tmp/backup-student-homes.py')
    homes = importlib.util.module_from_spec(spec); spec.loader.exec_module(homes)
    if homes.manifest(files / 'home') != json.loads((files / 'manifest.json').read_text()):
        raise RuntimeError('Pupil file content/metadata mismatch.')
    # File shares need traversal through these root-owned ancestors.
    BASE.chmod(0o711); files.chmod(0o711)
    lp = LoadParm(); lp.load(str(CONF))
    db = SamDB(url=str(RESTORED / 'private/sam.ldb'), session_info=system_session(), lp=lp)
    if db.get_domain_sid() != inventory['domain_sid']:
        raise RuntimeError('Domain SID changed.')
    for name, attrs in inventory['users'].items():
        row = db.search(expression='(sAMAccountName=' + ldb.binary_encode(name) + ')',
                        attrs=list(attrs))[0]
        actual = {key: [db.schema_format_value(key, value).decode() for value in row[key]]
                  for key in attrs if key in row}
        if actual != attrs:
            raise RuntimeError('Restored account differs: ' + name)
    output = inside(['samba-tool', 'dbcheck', '--cross-ncs', '-s', str(CONF)])
    (BASE / 'dbcheck.log').write_text(output)
    print('DOMAIN_SID_ACCOUNTS_FILES_DBCHECK_OK', flush=True)
    # Random test passwords affect ONLY the disposable restored domain copy.
    passwords = {name: 'Aa1!' + secrets.token_urlsafe(32) for name in ['student1', 'student2']}
    for name, password in passwords.items():
        db.setpassword('(sAMAccountName=' + name + ')', password)
    db = None
    krb = BASE / 'krb5-test.conf'
    krb.write_text('[libdefaults]\n default_realm = SCHOOL.TEST\n dns_lookup_kdc = false\n'
                   '[realms]\n SCHOOL.TEST = {\n  kdc = ' + IP + '\n }\n')
    log = (BASE / 'samba.log').open('w')
    process = subprocess.Popen(['ip', 'netns', 'exec', NS, 'samba', '-i', '--no-process-group',
                                '-s', str(CONF)], stdout=log, stderr=log, start_new_session=True)
    try:
        for attempt in range(30):
            if process.poll() is not None:
                raise RuntimeError('Restored Samba exited; inspect private samba.log.')
            try:
                inside(['python3', '-c',
                        'import socket; socket.create_connection(("' + IP + '", 88), 1).close()'])
                break
            except RuntimeError:
                time.sleep(1)
        else:
            raise RuntimeError('Restored KDC did not start.')
        inside(['samba_dnsupdate', '--configfile=' + str(CONF), '--use-samba-tool'], timeout=45)
        answer = inside(['dig', '@' + IP, 'school.test', 'SOA', '+short'])
        if not answer.strip():
            raise RuntimeError('DNS SOA missing.')
        srv = inside(['dig', '@' + IP, '_ldap._tcp.dc._msdcs.school.test', 'SRV', '+short'])
        address = inside(['dig', '@' + IP, 'sc-recovery.school.test', 'A', '+short'])
        if 'sc-recovery.school.test.' not in srv.lower() or IP not in address.splitlines():
            raise RuntimeError('Restored DC discovery records missing.')
        inside(['samba-tool', 'ntacl', 'sysvolcheck', '-s', str(CONF)])
        print('RESTORED_DNS_SRV_A_SYSVOL_ACL_OK', flush=True)
        for name, other in [('student1', 'student2'), ('student2', 'student1')]:
            account = pwd.getpwnam('SCHOOL\\' + name)
            if [account.pw_uid, account.pw_gid] != inventory['unix_ids'][name]:
                raise RuntimeError('Restored UID/GID mapping differs: ' + name)
            env = dict(os.environ, KRB5_CONFIG=str(krb), KRB5CCNAME='FILE:' + str(BASE / 'ticket'))
            env.pop('KRB5_TRACE', None)
            inside(['kinit', name + '@SCHOOL.TEST'], input=passwords[name] + '\n', env=env, timeout=20)
            inside(['klist', '-s'], env=env)
            (BASE / 'ticket').unlink(missing_ok=True)
            auth = BASE / 'smb-auth'
            auth.write_text('username = ' + name + '\npassword = ' + passwords[name] + '\ndomain = SCHOOL\n')
            probe = BASE / 'smb-probe.txt'; probe.write_text('Restored SMB write/read check\n')
            returned = BASE / 'smb-returned.txt'
            remote = '.recovery-' + secrets.token_hex(8) + '.txt'
            try:
                inside(['smbclient', '//' + IP + '/' + name, '-A', str(auth), '-c',
                        f'put {probe} {remote}; get {remote} {returned}; del {remote}'])
                if returned.read_bytes() != probe.read_bytes():
                    raise RuntimeError('SMB file roundtrip differs.')
                denied = subprocess.run(['ip', 'netns', 'exec', NS, 'smbclient',
                                         '//' + IP + '/' + other, '-A', str(auth), '-c', 'ls'],
                                        capture_output=True, text=True)
                if denied.returncode == 0 or 'NT_STATUS_ACCESS_DENIED' not in denied.stdout + denied.stderr:
                    raise RuntimeError('Expected explicit SMB access denied for peer share.')
            finally:
                auth.unlink(missing_ok=True); probe.unlink(missing_ok=True); returned.unlink(missing_ok=True)
            print(name + ': UID_KERBEROS_SMB_RW_PEER_DENIED_OK', flush=True)
    finally:
        (BASE / 'ticket').unlink(missing_ok=True)
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        process.wait(timeout=20)
        log.close()
    print('DOMAIN_RECOVERY_DRILL_OK; restored Samba stopped.', flush=True)
    (BASE / 'command-error.log').unlink(missing_ok=True)
    (BASE / 'recovery-result.json').write_text(json.dumps({
        'checked_utc': datetime.now(timezone.utc).isoformat(),
        'samba_version': inventory['samba_version'],
        'result': 'DOMAIN_RECOVERY_DRILL_OK',
        'checks': ['domain SID', 'student and Windows computer accounts',
                   'file contents and metadata', 'dbcheck', 'DNS SOA/SRV/A',
                   'SYSVOL ACL', 'UID/GID mapping', 'Kerberos', 'SMB read/write',
                   'SMB peer access denied'],
        'limits': ['No Windows client login against restored DC',
                   'Test pupil passwords reset only in disposable copy',
                   'Same Ubuntu ARM64 and Samba version as source',
                   'Authenticated RPC DNS updates used; TSIG path failed'],
    }, indent=2))


def main():
    if os.geteuid() != 0 or socket.gethostname() != 'school-recovery':
        raise SystemExit('Only run as root in the disposable school-recovery VM.')
    if Path('/var/lib/samba/private/sam.ldb').exists():
        raise SystemExit('Default AD database exists; refusing to use this VM.')
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'check'])
    parser.add_argument('archive', nargs='?', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        if args.archive is None:
            parser.error('prepare requires your trusted domain bundle')
        prepare(args.archive)
    else:
        check()


if __name__ == '__main__':
    main()
