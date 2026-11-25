# Private H: files on any classroom PC

Each account has AD `homeDrive=H:` and `homeDirectory=\\dc1.DOMAIN\pupils\LOGIN`. Standard Windows domain logon should map this drive on every joined PC. This shares files, not the local Windows desktop/profile. Teach pupils to save work to H:; if Desktop/Documents must also follow them, pilot a user Folder Redirection GPO separately with offline-files/conflict behavior reviewed.

Every pupil folder has a protected NT DACL granting that pupil Modify, SYSTEM Full Control and Domain Admins Full Control. SYSTEM owns the top folder so pupils cannot change its ACL or ownership. Other pupils and ordinary teachers have no access. Share-root authenticated users can list/traverse but cannot create folders; access-based listing hides unreadable folders. Privacy depends on the NT ACL, **not** hiding folder names. `acl_xattr` metadata must survive backups/restoration.

If H: is missing, inspect `net use` and the account's home attributes in RSAT or `samba-tool user show LOGIN`. Check DNS and TCP 445 first. As the signed-in pupil:

```powershell
net use H: \\dc1.ad.classroom.test\pupils\%USERNAME%
```

The `%USERNAME%` example is for `cmd.exe`; PowerShell uses `$env:USERNAME`:

```powershell
New-PSDrive -Name H -PSProvider FileSystem -Root "\\dc1.ad.classroom.test\pupils\$env:USERNAME" -Persist
```

For reliable policy deployment use RSAT Group Policy Management → User Configuration → Preferences → Windows Settings → Drive Maps, Update H: to `\\dc1.YOUR_DOMAIN\pupils\%USERNAME%`, targeting Pupils. Do not save alternate credentials in drive maps. Keep mapping consistent with AD home attributes. Enable 'Always wait for the network at computer startup and logon' on pilot computers if early logon prevents mapping.

Test own-folder save/read/delete. Try the other test login's UNC path explicitly and confirm access denied. Check denial in both directions. Do not fix access errors by granting Everyone/Domain Users Full Control, recursive chmod 777 or resetting SYSVOL ACLs blindly. Cached domain login may work while DC is off, but H: does not; offline files are not enabled by this project.
