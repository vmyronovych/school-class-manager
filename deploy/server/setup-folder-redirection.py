#!/usr/bin/env python3
"""Install a student-only Windows Folder Redirection GPO on the lab Samba DC."""
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone

POLICY_NAME = 'SCM - Student Documents and Desktop'
MARKER = 'Managed by school-class-manager lab/setup-folder-redirection.py'
EXTENSION = '[{25537BA6-77A8-11D2-9B6C-0000F8080861}{88E729D6-BDC1-11D1-BD2A-00C04FB9603F}]'
FOLDERS = {'{FDD39AD0-238F-46AF-ADB4-6C85480369C7}': 'Documents',
           '{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}': 'Desktop'}



def policy_bytes(group_sid, unc):
    # MS-GPFR v1: full path + move contents; leave folders on the server on removal.
    # Use the actual Windows format (MS-GPFR 4.2 and Samba's GPO backup fixture).
    # MS-GPFR 2.2.2 says VersionNumber; our policy using it hit Windows event 511.
    lines = ['[Version]', 'Version=100', '', '[Folder_Redirection]']
    lines += [f'{guid}={group_sid};' for guid in FOLDERS]
    for guid, folder in FOLDERS.items():
        lines += ['', f'[{guid}_{group_sid}]', 'Flags=1001', f'FullPath={unc}\\{folder}']
    return ('\r\n'.join(lines) + '\r\n').encode('utf-16')


def policy_version(existing, desired, current):
    if existing is None or existing == desired:
        return current or 65536
    legacy = desired.decode('utf-16').replace('Version=100', 'VersionNumber=100').encode('utf-16')
    if existing != legacy:
        raise RuntimeError('Policy file differs from managed settings; review first')
    if current >> 16 >= 65535:
        raise RuntimeError('User policy revision exhausted; review first')
    return current + 65536


def disable_share_caching(original):
    lines = original.splitlines(keepends=True)
    wanted = {'pupils', 'student1', 'student2'}
    found = set()
    result = []
    section = None
    for line in lines:
        match = re.match(r'^\s*\[([^]]+)\]', line)
        if match:
            section = match[1].lower()
            result.append(line)
            if section in wanted:
                if section in found:
                    raise RuntimeError('Duplicate managed share: ' + section)
                found.add(section)
                result.append('    csc policy = disable\n')
        elif section in wanted and re.match(r'^\s*csc\s+policy\s*=', line, re.I):
            continue
        else:
            result.append(line)
    if 'pupils' not in found:
        raise RuntimeError('Expected the pupils share')
    return ''.join(result)


def atomic_write(path, content, mode=0o644):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        output.write(content)
    try:
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    from samba import ldb
    from samba.auth import system_session
    from samba.dcerpc import security
    from samba.ndr import ndr_pack, ndr_unpack
    from samba.ntacls import dsacl2fsacl
    from samba.param import LoadParm
    from samba.provision import set_dir_acl
    from samba.samdb import SamDB
    from samba.samba3 import param as s3param, passdb

    if os.geteuid() != 0 or socket.gethostname() != 'school-server':
        raise SystemExit('Run with sudo on school-server.')
    os.umask(0o077)
    lp = LoadParm(); lp.load_default()
    realm = lp.get('realm').lower()
    unc = rf'\\school-server.{realm}\pupils'
    db = SamDB(url='/var/lib/samba/private/sam.ldb', session_info=system_session(), lp=lp)
    domain_dn = db.domain_dn()
    domain_sid = security.dom_sid(db.get_domain_sid())
    group = db.search(expression='(&(objectClass=group)(sAMAccountName=scm-students))', attrs=['objectSid'])
    if len(group) != 1:
        raise RuntimeError('Expected scm-students group')
    group_sid = db.schema_format_value('objectSid', group[0]['objectSid'][0]).decode()
    config = Path('/etc/samba/smb.conf')
    original = config.read_text()
    candidate = disable_share_caching(original)
    with tempfile.NamedTemporaryFile(mode='w', dir=config.parent) as check:
        check.write(candidate); check.flush()
        subprocess.run(['testparm', '-s', check.name], check=True, capture_output=True)
    policies_dn = 'CN=Policies,CN=System,' + domain_dn
    matches = db.search(base=policies_dn, expression='(displayName=' + POLICY_NAME + ')',
                        attrs=['cn', 'description', 'versionNumber', 'gPCFileSysPath', 'nTSecurityDescriptor'])
    if len(matches) > 1 or (matches and str(matches[0].get('description', [''])[0]) != MARKER):
        raise RuntimeError('Unmanaged or duplicate policy; review without overwriting')
    guid = str(matches[0]['cn'][0]) if matches else '{' + str(uuid.uuid4()).upper() + '}'
    gpo_dn = 'CN=' + guid + ',' + policies_dn
    policy = Path('/var/lib/samba/sysvol') / realm / 'Policies' / guid
    ini = policy / 'User' / 'Documents & Settings' / 'fdeploy1.ini'
    content = policy_bytes(group_sid, unc)
    if policy.exists() and not matches:
        raise RuntimeError('Unmanaged policy directory exists')
    # Never overwrite policy edits made independently in Windows GPMC.
    previous = ini.read_bytes() if ini.exists() else None
    current = int(str(matches[0]['versionNumber'][0])) if matches else 0
    version = policy_version(previous, content, current)
    template = db.search(base='CN={31B2F340-016D-11D2-945F-00C04FB984F9},' + policies_dn,
                         scope=ldb.SCOPE_BASE, attrs=['nTSecurityDescriptor'])[0]
    sddl = ndr_unpack(security.descriptor, template['nTSecurityDescriptor'][0]).as_sddl(domain_sid)
    apply_ace = '(OA;CI;CR;edacfd8f-ffb3-11d1-b41d-00a0c968f939;;AU)'
    if sddl.count(apply_ace) != 1:
        raise RuntimeError('Unexpected default GPO ACL; refusing to guess')
    sddl = sddl.replace(apply_ace, apply_ace.replace(';;AU)', ';;' + group_sid + ')'))
    descriptor = security.descriptor.from_sddl(sddl, domain_sid)
    links = str(db.search(base=domain_dn, scope=ldb.SCOPE_BASE, attrs=['gPLink'])[0].get('gPLink', [''])[0])
    backup = Path('/var/lib/scm-directory/folder-redirection')
    backup.mkdir(mode=0o700, parents=True, exist_ok=True)
    if previous is not None and previous != content:
        snapshot = backup / 'fdeploy1.ini.before-header-fix'
        if not snapshot.exists():
            atomic_write(snapshot, previous, 0o600)
    if not (backup / 'before.json').exists():
        atomic_write(backup / 'smb.conf.before', original.encode(), 0o600)
        atomic_write(backup / 'before.json', json.dumps({'at': datetime.now(timezone.utc).isoformat(),
                     'gpo': guid, 'domainLinks': links, 'policyExisted': bool(matches)}, indent=2).encode(), 0o600)

    def replace(dn, values):
        message = ldb.Message(); message.dn = ldb.Dn(db, dn)
        for key, value in values.items():
            message[key] = ldb.MessageElement(value, ldb.FLAG_MOD_REPLACE, key)
        db.modify(message)

    if not matches:
        db.transaction_start()
        try:
            db.add({'dn': gpo_dn, 'objectClass': 'groupPolicyContainer', 'displayName': POLICY_NAME,
                    'description': MARKER, 'flags': '3', 'gPCFunctionalityVersion': '2',
                    'gPCFileSysPath': rf'\\{realm}\sysvol\{realm}\Policies' + '\\' + guid,
                    'versionNumber': '0', 'nTSecurityDescriptor': ndr_pack(descriptor)})
            for child in ['User', 'Machine']:
                db.add({'dn': 'CN=' + child + ',' + gpo_dn, 'objectClass': 'container'})
            db.transaction_commit()
        except Exception:
            db.transaction_cancel(); raise
    # The new policy remains unlinked and disabled until its files and ACL exist.
    ini.parent.mkdir(parents=True, exist_ok=True)
    (policy / 'Machine').mkdir(exist_ok=True)
    atomic_write(ini, content)
    atomic_write(policy / 'GPT.INI', f'[General]\r\nVersion={version}\r\n'.encode())
    actual_sd = db.search(base=gpo_dn, scope=ldb.SCOPE_BASE, attrs=['nTSecurityDescriptor'])[0]['nTSecurityDescriptor'][0]
    acl = ndr_unpack(security.descriptor, actual_sd).as_sddl(domain_sid)
    s3conf = s3param.get_context(); s3conf.load(lp.configfile)
    s3conf.set('passdb backend', 'samba_dsdb:' + db.url)
    passdb.reload_static_pdb()
    pdb = passdb.PDB(s3conf.get('passdb backend'))
    set_dir_acl(str(policy), dsacl2fsacl(acl, domain_sid), lp, str(domain_sid), False, passdb=pdb)
    if candidate != original:
        atomic_write(config, candidate.encode())
        subprocess.run(['smbcontrol', 'all', 'reload-config'], check=True)
    db.transaction_start()
    try:
        replace(gpo_dn, {'flags': '2', 'gPCUserExtensionNames': EXTENSION, 'versionNumber': str(version)})
        link = '[LDAP://' + gpo_dn + ';0]'
        if gpo_dn.casefold() not in links.casefold():
            replace(domain_dn, {'gPLink': links + link})
        elif link.casefold() not in links.casefold():
            raise RuntimeError('Existing policy link has unexpected options')
        db.transaction_commit()
    except Exception:
        db.transaction_cancel(); raise
    atomic_write(backup / 'policy.json', json.dumps({'name': POLICY_NAME, 'guid': guid, 'groupSid': group_sid,
                 'path': str(ini), 'unc': unc, 'version': version}, indent=2).encode(), 0o600)
    print('FOLDER_REDIRECTION_POLICY_READY', guid)
    print('Documents -> ' + unc + r'\Documents')
    print('Desktop -> ' + unc + r'\Desktop')
    print('Windows application pending: refresh user policy and sign out/in as a pupil.')


if __name__ == '__main__':
    main()
