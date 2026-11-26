#!/usr/bin/env python3
"""Manual lab file backup and isolated restore check. Does not back up the AD domain."""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import socket
import stat
import subprocess
import tarfile
import tempfile
import uuid

ROOT = Path('/srv/school/home')
FLAGS = ['--acls', '--xattrs', '--xattrs-include=*', '--numeric-owner']


def digest(path):
    with path.open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def manifest(root):
    result = {}
    for path in [root, *sorted(root.rglob('*'))]:
        info = path.lstat()
        if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
            raise RuntimeError(f'Lab backup supports only regular files/directories: {path}')
        result[str(path.relative_to(root))] = {
            'mode': stat.S_IMODE(info.st_mode), 'uid': info.st_uid, 'gid': info.st_gid,
            'sha256': digest(path) if path.is_file() else None,
            'xattrs': {key: base64.b64encode(os.getxattr(path, key)).decode('ascii')
                      for key in os.listxattr(path)},
        }
    return result


def verify(archive):
    # Accept only this helper's file-only archive layout, before extracting as root.
    with tarfile.open(archive) as source:
        for member in source:
            path = PurePosixPath(member.name)
            if (path.is_absolute() or '..' in path.parts
                    or not path.parts or path.parts[0] not in ('home', 'manifest.json')
                    or not (member.isfile() or member.isdir())):
                raise RuntimeError('Unexpected archive member; refusing extraction.')
    with tempfile.TemporaryDirectory(prefix='scm-restore-', dir='/var/tmp') as stage:
        subprocess.run(['tar', *FLAGS, '--same-owner', '--same-permissions',
                        '-xzf', str(archive), '-C', stage], check=True)
        expected = json.loads((Path(stage) / 'manifest.json').read_text())
        restored = Path(stage) / 'home'
        if manifest(restored) != expected:
            raise RuntimeError('Restore differs: contents, owner, mode, or extended attributes.')
        # Make only the temporary parent traversable for the pupil identity checks.
        Path(stage).chmod(0o711)
        for name, other in [('student1', 'student2'), ('student2', 'student1')]:
            own = subprocess.run(['runuser', '-u', 'SCHOOL\\' + name, '--',
                                  'ls', str(restored / name)], capture_output=True)
            peer = subprocess.run(['runuser', '-u', 'SCHOOL\\' + other, '--',
                                   'ls', str(restored / name)], capture_output=True)
            if own.returncode != 0 or peer.returncode == 0:
                raise RuntimeError('Restored folder access check failed.')
        print('RESTORE_OK: contents, UID/GID, modes, xattrs, pupil isolation.')


def backup():
    owner = pwd.getpwnam('SCHOOL\\student1')
    host_user = pwd.getpwnam('ubuntu')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    token = uuid.uuid4().hex[:12]
    probe = ROOT / 'student1' / f'.restore-check-{token}.txt'
    archive = Path('/home/ubuntu') / f'school-homes-{stamp}-{token}.tar.gz'
    with probe.open('x') as file:
        file.write('Disposable school lab restore check\n')
    try:
        probe.chmod(0o600)
        os.chown(probe, owner.pw_uid, owner.pw_gid)
        os.setxattr(probe, 'user.scm.restore-check', b'preserve-this-attribute')
        with tempfile.TemporaryDirectory(prefix='scm-backup-') as stage:
            (Path(stage) / 'manifest.json').write_text(json.dumps(manifest(ROOT), sort_keys=True))
            subprocess.run(['tar', *FLAGS, '-czf', str(archive),
                            '-C', stage, 'manifest.json', '-C', str(ROOT.parent), 'home'], check=True)
        # Delete only our disposable source file, then prove it can be restored.
        probe.unlink()
        verify(archive)
        os.chown(archive, host_user.pw_uid, host_user.pw_gid)
        archive.chmod(0o600)
    except Exception:
        archive.unlink(missing_ok=True)
        raise
    finally:
        probe.unlink(missing_ok=True)
    print('ARCHIVE=' + str(archive))
    with archive.open('rb') as file:
        print('SHA256=' + hashlib.file_digest(file, 'sha256').hexdigest())


def main():
    if os.geteuid() != 0 or socket.gethostname() != 'school-server':
        raise SystemExit('Run as root inside the school-server lab VM.')
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['backup', 'verify'])
    parser.add_argument('archive', nargs='?', type=Path)
    args = parser.parse_args()
    if args.action == 'backup':
        if args.archive:
            parser.error('backup generates a unique archive name automatically')
        backup()
    else:
        if not args.archive:
            parser.error('verify requires the archive path')
        verify(args.archive.resolve(strict=True))


if __name__ == '__main__':
    main()
