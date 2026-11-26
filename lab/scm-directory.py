#!/usr/bin/python3 -I
"""Narrow root bridge for the pupil panel. One JSON request on stdin; never shell passwords."""
import fcntl
import base64
import errno
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import sqlite3
import stat
import sys
import time
from datetime import datetime, timezone
from contextlib import ExitStack

from samba import ldb, gensec
from samba.auth import system_session
from samba.credentials import Credentials, MUST_USE_KERBEROS
from samba.param import LoadParm
from samba.samdb import SamDB

STUDENTS = 'scm-students'
TEACHERS = 'vchyteli'
STATE = Path('/var/lib/scm-directory')
HOMES = Path('/srv/school/home')

class Refused(Exception):
    pass

def name(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z][a-z0-9.-]{0,63}', value):
        raise Refused('validation')
    return value

def text(row, key, default=''):
    return str(row[key][0]) if key in row else default

def pupil_password(*identity):
    """Seven characters: the lab domain minimum, chosen for pupil usability."""
    # Upper/lower case and digits satisfy complexity; no l/I, 0 or 1.
    consonants, vowels = 'bcdfghkmnprstvwz', 'aeiou'
    forbidden = {part.lower() for value in identity for part in [value, *re.split(r'[\W_]+', value)]
                 if len(part) >= 3}
    for _ in range(100):
        block = ''.join(secrets.choice(consonants) + secrets.choice(vowels)
                        for _ in range(2)).capitalize()
        password = block + ''.join(secrets.choice('23456789') for _ in range(3))
        if not any(part in password.lower() for part in forbidden):
            return password
    raise Refused('unavailable')

def user(db, login):
    rows = db.search(expression='(&(objectClass=user)(sAMAccountName=' + ldb.binary_encode(login) + '))', attrs=[])
    if len(rows) != 1:
        raise Refused('not_found')
    return db.search(base=rows[0].dn, scope=ldb.SCOPE_BASE,
                     attrs=['sAMAccountName', 'displayName', 'givenName', 'sn', 'objectSid',
                            'userAccountControl', 'primaryGroupID', 'adminCount', 'homeDirectory', 'tokenGroups'])[0]

def sid(db, row):
    return db.schema_format_value('objectSid', row['objectSid'][0]).decode()

def member(db, row, group):
    groups = db.search(expression='(&(objectClass=group)(sAMAccountName=' + ldb.binary_encode(group) + '))', attrs=[])
    if len(groups) != 1:
        return False
    return bool(db.search(base=row.dn, scope=ldb.SCOPE_BASE,
                         expression='(memberOf:1.2.840.113556.1.4.1941:=' + ldb.binary_encode(str(groups[0].dn)) + ')', attrs=[]))

def privileged(db, row):
    if text(row, 'adminCount') == '1' or text(row, 'primaryGroupID') != '513':
        return True
    domain = db.get_domain_sid()
    forbidden = {domain + '-' + str(rid) for rid in [500, 502, 512, 516, 518, 519, 520, 521, 526, 527]}
    forbidden.update('S-1-5-32-' + str(rid) for rid in [544, 548, 549, 550, 551, 552])
    tokens = {db.schema_format_value('objectSid', raw).decode() for raw in row.get('tokenGroups', [])}
    return sid(db, row) in forbidden or bool(tokens & forbidden)

def teacher(db, login, expected_sid=None):
    # AD names are case-insensitive; directory spelling and existing cookies may
    # contain capitals (notably the built-in Administrator account).
    login = name(login.lower() if isinstance(login, str) else login)
    row = user(db, login)
    actual_sid = sid(db, row)
    if int(text(row, 'userAccountControl')) & 2 or (expected_sid is not None and actual_sid != expected_sid):
        raise Refused('forbidden')
    is_admin = member(db, row, 'Domain Admins') or text(row, 'primaryGroupID') == '512'
    if not is_admin and not member(db, row, TEACHERS):
        raise Refused('forbidden')
    return {'login': login, 'displayName': text(row, 'displayName', login),
            'role': 'Admin' if is_admin else 'Teacher', 'sid': actual_sid}

def pupil(db, row):
    return member(db, row, STUDENTS) and not member(db, row, TEACHERS) and not privileged(db, row)

def authenticate(db, lp, request):
    login = name(request.get('login'))
    password = request.get('password')
    if not isinstance(password, str) or not password or len(password) > 256:
        raise Refused('credentials')
    credentials = Credentials()
    credentials.guess(lp)
    credentials.set_username(login)
    credentials.set_password(password)
    credentials.set_domain(lp.get('workgroup'))
    credentials.set_realm(lp.get('realm'))
    credentials.set_kerberos_state(MUST_USE_KERBEROS)
    credentials.set_gensec_features(credentials.get_gensec_features() | gensec.FEATURE_SEAL)
    try:
        connection = SamDB(url='ldap://school-server.school.test', credentials=credentials, lp=lp)
        connection.search(base='', scope=ldb.SCOPE_BASE, attrs=['defaultNamingContext'])
    except ldb.LdbError:
        raise Refused('credentials') from None
    return teacher(db, login)

def audit(connection, actor, action, target, result):
    connection.execute('INSERT INTO events (at,actor,action,target,result) VALUES (?,?,?,?,?)',
                       (datetime.now(timezone.utc).isoformat(), actor, action, target, result))
    connection.commit()

def mutate(db, request, actor):
    login = name(request.get('login'))
    action = request['op']
    with (STATE / 'mutation.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with sqlite3.connect(STATE / 'journal.sqlite3') as journal:
            journal.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY,at TEXT,actor TEXT,action TEXT,target TEXT,result TEXT)')
            audit(journal, actor['login'], action, login, 'Started')
            created = False
            try:
                if action == 'reset':
                    row = user(db, login)
                    if not pupil(db, row):
                        raise Refused('forbidden')
                    password = pupil_password(login, text(row, 'displayName'), text(row, 'givenName'), text(row, 'sn'))
                    db.setpassword('(sAMAccountName=' + ldb.binary_encode(login) + ')', password)
                else:
                    gn, sn = request.get('givenName'), request.get('surname')
                    for value in [gn, sn]:
                        if not isinstance(value, str) or not value.strip() or len(value) > 64 or any(ord(c) < 32 for c in value):
                            raise Refused('validation')
                    existing = db.search(expression='(sAMAccountName=' + ldb.binary_encode(login) + ')', attrs=[])
                    path = HOMES / login
                    if existing or path.exists() or path.is_symlink():
                        raise Refused('exists')
                    password = pupil_password(login, gn, sn)
                    # Commit a disabled account first: failures cannot leave a usable incomplete pupil.
                    db.transaction_start()
                    try:
                        db.newuser(login, password, givenname=gn.strip(), surname=sn.strip(),
                                   homedrive='H:', homedirectory=r'\\school-server.school.test\pupils')
                        db.disable_account('(sAMAccountName=' + ldb.binary_encode(login) + ')')
                        db.add_remove_group_members(STUDENTS, [login], add_members_operation=True)
                        db.transaction_commit()
                    except Exception:
                        db.transaction_cancel()
                        raise
                    created = True
                    for attempt in range(10):
                        try:
                            account = pwd.getpwnam('SCHOOL\\' + login)
                            break
                        except KeyError:
                            if attempt == 9:
                                raise Refused('partial') from None
                            time.sleep(0.5)
                    path.mkdir(mode=0o700)
                    os.chown(path, account.pw_uid, account.pw_gid)
                    db.enable_account('(sAMAccountName=' + ldb.binary_encode(login) + ')')
                audit(journal, actor['login'], action, login, 'Succeeded')
                return {'login': login, 'password': password}
            except Exception:
                if created:
                    db.disable_account('(sAMAccountName=' + ldb.binary_encode(login) + ')')
                audit(journal, actor['login'], action, login, 'Failed')
                if created:
                    raise Refused('partial') from None
                raise

def pupil_files(db, request):
    login = name(request.get('login'))
    if not pupil(db, user(db, login)):
        raise Refused('forbidden')
    path = request.get('path', '')
    if not isinstance(path, str) or len(path) > 2048 or '\\' in path or any(ord(c) < 32 for c in path):
        raise Refused('invalid_path')
    parts = path.split('/') if path else []
    if any(part in ('', '.', '..') for part in parts):
        raise Refused('invalid_path')
    download = request['op'] == 'download'
    if download and not parts:
        raise Refused('invalid_path')
    uid = pwd.getpwnam('SCHOOL\\' + login).pw_uid
    # Open every component relative to an already-open directory. Never resolve
    # student-controlled symlinks or expose arbitrary root-readable files.
    try:
        with ExitStack() as stack:
            def open_at(component, parent=None, directory=True):
                flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                if directory:
                    flags |= os.O_DIRECTORY
                fd = os.open(component, flags, dir_fd=parent)
                stack.callback(os.close, fd)
                return fd
            parent = open_at(str(HOMES))
            parent = open_at(login, parent)
            for component in (parts[:-1] if download else parts):
                parent = open_at(component, parent)
            if download:
                fd = open_at(parts[-1], parent, directory=False)
                metadata = os.fstat(fd)
                if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_uid != uid:
                    raise Refused('forbidden')
                limit = 20 * 1024 * 1024
                if metadata.st_size > limit:
                    raise Refused('file_too_large')
                with os.fdopen(os.dup(fd), 'rb') as source:
                    content = source.read(limit + 1)
                if len(content) > limit:
                    raise Refused('file_too_large')
                return {'name': parts[-1], 'content': base64.b64encode(content).decode('ascii')}
            result = []
            with os.scandir(parent) as entries:
                for count, entry in enumerate(entries):
                    if count >= 2000:
                        raise Refused('too_many_files')
                    try:
                        metadata = entry.stat(follow_symlinks=False)
                    except FileNotFoundError:
                        continue
                    directory = stat.S_ISDIR(metadata.st_mode)
                    if not directory and (not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_uid != uid):
                        continue
                    result.append({'name': entry.name, 'directory': directory,
                                   'size': None if directory else metadata.st_size,
                                   'modified': datetime.fromtimestamp(metadata.st_mtime, timezone.utc).isoformat()})
            return sorted(result, key=lambda item: (not item['directory'], item['name'].casefold()))
    except FileNotFoundError:
        raise Refused('file_not_found') from None
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.ENOTDIR, errno.EACCES):
            raise Refused('forbidden') from None
        raise

def main():
    if os.geteuid() != 0 or len(sys.argv) != 1:
        raise Refused('forbidden')
    os.umask(0o077)
    request = json.loads(sys.stdin.read(16385))
    if not isinstance(request, dict):
        raise Refused('validation')
    lp = LoadParm(); lp.load_default()
    if lp.get('realm') != 'SCHOOL.TEST':
        raise Refused('unavailable')
    db = SamDB(url='/var/lib/samba/private/sam.ldb', session_info=system_session(), lp=lp)
    operation = request.get('op')
    if operation == 'authenticate':
        return authenticate(db, lp, request)
    raw_actor = request.get('actor', {})
    if not isinstance(raw_actor.get('sid'), str):
        raise Refused('forbidden')
    actor = teacher(db, raw_actor.get('login'), raw_actor['sid'])
    if operation == 'session':
        return actor
    if operation in ['files', 'download']:
        return pupil_files(db, request)
    if operation == 'list':
        rows = db.search(expression='(&(objectClass=user)(!(objectClass=computer)))', attrs=['sAMAccountName'])
        result = []
        for item in rows:
            row = user(db, text(item, 'sAMAccountName'))
            if pupil(db, row):
                login = text(row, 'sAMAccountName')
                result.append({'login': login, 'displayName': text(row, 'displayName', login),
                               'enabled': not bool(int(text(row, 'userAccountControl')) & 2),
                               'homeDirectory': text(row, 'homeDirectory') or None})
        return sorted(result, key=lambda row: row['login'])
    if operation in ['create', 'reset']:
        return mutate(db, request, actor)
    raise Refused('validation')

if __name__ == '__main__':
    try:
        response = {'data': main()}
    except Refused as error:
        response = {'error': str(error)}
    except (ValueError, TypeError, KeyError):
        response = {'error': 'validation'}
    except Exception:
        response = {'error': 'unavailable'}
    print(json.dumps(response, ensure_ascii=True))
