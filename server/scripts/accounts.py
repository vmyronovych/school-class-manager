#!/usr/bin/python3
"""Local administrator account management via Samba API, interactive secrets."""
import argparse, getpass, json, os, pathlib, re, subprocess

def main():
    assert os.geteuid() == 0, 'Run with sudo'
    from samba.samdb import SamDB
    from samba.param import LoadParm
    from samba.auth import system_session
    from samba.dcerpc import security
    from samba.ndr import ndr_unpack
    import ldb
    lp = LoadParm()
    lp.load('/etc/samba/smb.conf')
    db = SamDB(url=lp.private_path('sam.ldb'), session_info=system_session(), lp=lp)
    sid = str(db.get_domain_sid())
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['init-share', 'create', 'reset', 'disable', 'enable', 'list'])
    p.add_argument('username', nargs='?')
    p.add_argument('--role', choices=['pupil', 'teacher', 'admin'], default='pupil')
    a = p.parse_args()
    base = pathlib.Path('/srv/classroom/homes')

    def acl(path, sddl):
        subprocess.run(['samba-tool', 'ntacl', 'set', sddl, str(path), '--use-s3fs', '--service=pupils'], check=True, stdout=subprocess.DEVNULL)

    if a.action == 'init-share':
        # Authenticated users can traverse/list root; child DACLs are private.
        # No create/delete-child grant at share root.
        base.chmod(0o755)
        acl(base, f'O:SYG:SYD:P(A;;0x1200a9;;;AU)(A;OICI;FA;;;{sid}-512)(A;OICI;FA;;;SY)')
        return
    if a.action == 'list':
        for entry in db.search(base=db.domain_dn(), expression='(&(objectClass=user)(!(objectClass=computer)))', attrs=['sAMAccountName']):
            print(str(entry['sAMAccountName'][0]))
        return
    user = a.username or ''
    assert re.fullmatch(r'[a-z][a-z0-9._-]{0,31}', user), 'Use a simple lowercase login'
    entries = db.search(base=db.domain_dn(), expression=f'(&(objectClass=user)(sAMAccountName={ldb.binary_encode(user)}))', attrs=['objectSid', 'memberOf'])
    if a.action == 'create':
        assert not entries, 'Account already exists; no password or ACL changed'
        assert not (base / user).exists(), 'Existing folder: investigate before account reuse'
        password = getpass.getpass('Initial password (14+ characters): ')
        assert len(password) >= 14
        assert password == getpass.getpass('Repeat password: ')
        c = json.loads(pathlib.Path('/etc/classroom/config.json').read_text())
        home = f"\\\\{c['hostname']}.{c['realm'].lower()}\\pupils\\{user}"
        db.newuser(user, password, homedrive='H:', homedirectory=home)
        del password
        group = {'pupil': 'Pupils', 'teacher': 'Teachers', 'admin': 'Domain Admins'}[a.role]
        db.add_remove_group_members(group, [user], add_members_operation=True)
        # Password must be changed at first real pupil login; admin/teacher too.
        db.force_password_change_at_next_login(f'sAMAccountName={ldb.binary_encode(user)}')
        entries = db.search(base=db.domain_dn(), expression=f'(sAMAccountName={ldb.binary_encode(user)})', attrs=['objectSid'])
        usid = str(ndr_unpack(security.dom_sid, bytes(entries[0]['objectSid'][0])))
        folder = base / user
        folder.mkdir(mode=0o700)
        # SYSTEM owns the top folder: pupil gets Modify, not WRITE_DAC/WRITE_OWNER.
        acl(folder, f'O:SYG:SYD:P(A;OICI;0x1301bf;;;{usid})(A;OICI;FA;;;{sid}-512)(A;OICI;FA;;;SY)')
        print(f'{user} created as {a.role}; private H: folder ready.')
        return
    assert entries, 'Account not found'
    filt = f'sAMAccountName={ldb.binary_encode(user)}'
    if a.action == 'reset':
        password = getpass.getpass('New temporary password (14+ characters): ')
        assert len(password) >= 14
        assert password == getpass.getpass('Repeat password: ')
        db.setpassword(filt, password, force_change_at_next_login=True)
        del password
    elif a.action == 'disable':
        db.disable_account(filt)
    elif a.action == 'enable':
        db.enable_account(filt)
    print('Account updated; files retained.')

if __name__ == '__main__':
    main()
