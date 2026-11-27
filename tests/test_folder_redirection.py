#!/usr/bin/env python3
"""Pure configuration tests; no Samba, Windows or root permissions needed."""
import configparser
from pathlib import Path
import runpy
import unittest

module = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'deploy/server/setup-folder-redirection.py'))


class FolderRedirectionTests(unittest.TestCase):
    def test_native_windows_format_preserves_contents_and_targets_only_students(self):
        sid = 'S-1-5-21-1-2-3-1100'
        raw = module['policy_bytes'](sid, r'\\school-server.school.test\pupils')
        self.assertTrue(raw.startswith(b'\xff\xfe'))
        ini = configparser.ConfigParser(interpolation=None)
        ini.read_string(raw.decode('utf-16'))
        # Microsoft MS-GPFR 4.2 and Samba's generalized-gpo-backup fixture
        # both use the key "version", unlike the prose in MS-GPFR 2.2.2.
        self.assertEqual(dict(ini['Version']), {'version': '100'})
        for guid, folder in module['FOLDERS'].items():
            self.assertEqual(ini['Folder_Redirection'][guid], sid + ';')
            rule = ini[guid + '_' + sid]
            flags = int(rule['Flags'], 16)
            self.assertTrue(flags & 0x1000)  # Full UNC path
            self.assertTrue(flags & 1)  # Move existing files
            self.assertFalse(flags & 0x20)  # Keep server files on policy removal
            self.assertFalse(flags & 0x10)  # Keep the existing private share ACLs
            self.assertEqual(rule['FullPath'], r'\\school-server.school.test\pupils' + '\\' + folder)
        self.assertNotIn('S-1-1-0', raw.decode('utf-16'))

    def test_caching_change_is_idempotent_and_preserves_other_settings(self):
        source = '[global]\n    workgroup = SCHOOL\n[student1]\n    path = /one\n[student2]\n    csc policy = manual\n[pupils]\n    valid users = @scm-students\n[other]\n    csc policy = documents\n'
        changed = module['disable_share_caching'](source)
        self.assertEqual(changed, module['disable_share_caching'](changed))
        self.assertEqual(changed.count('csc policy = disable'), 3)
        self.assertIn('[other]\n    csc policy = documents', changed)
        self.assertIn('path = /one', changed)
        self.assertIn('valid users = @scm-students', changed)

    def test_missing_share_fails_instead_of_applying_partial_config(self):
        with self.assertRaises(RuntimeError):
            module['disable_share_caching']('[other]\npath=/example\n')

    def test_known_old_header_migrates_once_and_bumps_user_revision(self):
        desired = module['policy_bytes']('S-1-5-21-1-2-3-1100', r'\\school-server.school.test\pupils')
        old = desired.decode('utf-16').replace('Version=100', 'VersionNumber=100').encode('utf-16')
        self.assertEqual(module['policy_version'](old, desired, 65536), 131072)
        self.assertEqual(module['policy_version'](desired, desired, 131072), 131072)
        with self.assertRaises(RuntimeError):
            module['policy_version'](old + b'\x00\x00', desired, 65536)


if __name__ == '__main__':
    unittest.main()
