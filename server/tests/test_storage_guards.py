"""Local regression tests for destructive-storage guards; all OS calls mocked.
These are not substitutes for an actual Samba restoration drill.
"""
import importlib.util
import json
import pathlib
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPT = pathlib.Path(__file__).parents[1] / 'scripts/setup.py'
spec = importlib.util.spec_from_file_location('classroom_setup', SCRIPT)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)
NativePath = pathlib.Path


class StorageGuards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = NativePath(self.tmp.name)
        self.config = {'mode': 'lab', 'confirmed': False, 'realm': 'AD.CLASSROOM.TEST',
                       'domain': 'CLASSROOM', 'hostname': 'dc1', 'ip': '192.168.77.10',
                       'netmask': '255.255.255.0', 'state_disk_mb': 65536,
                       'initialize_storage': False}
        for name in ('etc/classroom', 'etc/netplan', 'etc/samba', 'etc/chrony/conf.d',
                     'var/lib/samba', 'dev', 'srv'):
            (self.root / name).mkdir(parents=True)
        (self.root / 'dev/sdb').touch()
        (self.root / 'etc/fstab').write_text('# unrelated entry retained\n')
        self.save_config()
        self.fs = 'ext4'
        self.size = 65536 * 1024 * 1024
        self.children = None
        self.signatures = []
        self.calls = []
        self.mounts = set()
        self.path_patch = patch.object(setup.pathlib, 'Path', self.path)
        self.run_patch = patch.object(setup, 'run', self.mock_run)
        self.subprocess_patch = patch.object(setup.subprocess, 'run', self.subprocess)
        self.path_patch.start(); self.run_patch.start(); self.subprocess_patch.start()

    def tearDown(self):
        self.subprocess_patch.stop(); self.run_patch.stop(); self.path_patch.stop()
        self.tmp.cleanup()

    def path(self, value):
        return self.root / str(value).lstrip('/')

    def save_config(self):
        (self.root / 'etc/classroom/config.json').write_text(json.dumps(self.config))

    def subprocess(self, args, **kw):
        if args[0] == 'blkid':
            return types.SimpleNamespace(returncode=0 if self.fs else 2)
        if args[0] == 'mountpoint':
            return types.SimpleNamespace(returncode=0 if args[-1] in self.mounts else 1)
        raise AssertionError(f'Unexpected OS operation: {args}')

    def mock_run(self, *args, **kw):
        self.calls.append(args)
        out = ''
        if args[0] == 'lsblk':
            d = {'name': 'sdb', 'type': 'disk', 'size': self.size}
            if self.children:
                d['children'] = self.children
            out = json.dumps({'blockdevices': [d]})
        elif args[0] == 'blkid':
            out = self.fs if 'TYPE' in args else 'test-uuid'
        elif args[0] == 'wipefs':
            out = json.dumps({'signatures': self.signatures})
        elif args[0] == 'mkfs.ext4':
            self.fs = 'ext4'
        elif args[0] == 'mount':
            self.mounts.add(args[-1])
        elif args[0] not in ('ip', 'netplan', 'systemctl', 'chgrp'):
            raise AssertionError(f'Unexpected operation: {args}')
        return types.SimpleNamespace(stdout=out, returncode=0)

    def no_format(self):
        self.assertFalse(any(c[0] == 'mkfs.ext4' for c in self.calls))

    def test_empty_disk_requires_explicit_approval(self):
        self.fs = ''
        with self.assertRaisesRegex(AssertionError, 'Refusing format'):
            setup.main()
        self.no_format()

    def test_signature_never_formatted_even_with_approval(self):
        self.fs = ''; self.signatures = [{'type': 'gpt'}]
        self.config['initialize_storage'] = True; self.save_config()
        with self.assertRaisesRegex(AssertionError, 'Refusing format'):
            setup.main()
        self.no_format()

    def test_wrong_filesystem_never_formatted(self):
        self.fs = 'ntfs'; self.config['initialize_storage'] = True; self.save_config()
        with self.assertRaisesRegex(AssertionError, 'Unexpected filesystem'):
            setup.main()
        self.no_format()

    def test_wrong_size_never_formatted(self):
        self.size = 1234
        with self.assertRaisesRegex(AssertionError, 'Unexpected disk size'):
            setup.main()
        self.no_format()

    def test_partitioned_disk_never_formatted(self):
        self.children = [{'name': 'sdb1'}]
        with self.assertRaisesRegex(AssertionError, 'unpartitioned'):
            setup.main()
        self.no_format()

    def test_approved_blank_format_once_then_safe_rerun(self):
        self.fs = ''; self.config['initialize_storage'] = True; self.save_config()
        setup.main(); setup.main()
        self.assertEqual(sum(c[0] == 'mkfs.ext4' for c in self.calls), 1)
        fstab = (self.root/'etc/fstab').read_text()
        self.assertEqual(fstab.count('UUID=test-uuid'), 1)
        self.assertEqual(fstab.count('/srv/classroom/state /var/lib/samba'), 1)
        self.assertIn('# unrelated entry retained', fstab)

    def test_identity_change_rejected_without_format(self):
        setup.main()
        self.config['realm'] = 'OTHER.CLASSROOM.TEST'; self.save_config()
        with self.assertRaisesRegex(AssertionError, 'Identity mismatch'):
            setup.main()
        self.no_format()

    def test_existing_domain_without_identity_rejected(self):
        (self.root/'srv/classroom/domain').mkdir(parents=True)
        with self.assertRaisesRegex(AssertionError, 'Unrecognized existing domain'):
            setup.main()
        self.no_format()

    def test_missing_database_never_becomes_empty_rebuild(self):
        setup.main()
        (self.root/'srv/classroom/domain-ready').touch()
        with self.assertRaisesRegex(AssertionError, 'Ready marker without AD DB'):
            setup.main()
        self.no_format()


if __name__ == '__main__':
    unittest.main()
