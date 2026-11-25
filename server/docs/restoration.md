# Restore the existing domain

Empty provisioning prepares storage/packages. `domain.py create` generates a **new SID** even when the names are identical. Restoration must recover old accounts/password hashes, computer trust secrets, SYSVOL, identity and private files.

Stop the original DC before a restored copy can reach its network. Keep original disk and backups untouched. Use a **new external empty VDI**, original realm/domain/hostname/IP/netmask and isolated `mode=recovery`. Recovery permits the original production realm without LAN exposure and forbids new domain creation. For the .TEST lab drill mode=lab is also supported.

1. Set `CLASSROOM_CONFIG` to a separate recovery configuration and new VDI path. Create it with New-StateDisk.ps1, approve first format only, and `vagrant up server`. Do **not** create a domain. Set initialize_storage=false after format.
2. Recover the exact matching guest package environment. Cold restore refuses a different package lock; preserve powered-off matching OS image/package cache before updates. If binaries are unavailable, the official AD recovery route with a supported Samba version requires a separately reviewed isolated procedure and full trust/ACL validation; it is not automatically tested here.
3. Copy/decrypt the backup into root-only guest storage. Extract its outer archive into a private directory, preserving the inner COMPLETE/checksum set.
4. Run `sudo /usr/local/lib/classroom/restore.sh /root/backup/TIMESTAMP RESTORE_EXISTING_DOMAIN`. It checks hashes, versions, identity, archive paths and empty domain/home destination, then restores ACLs/xattrs/owners and starts/checks Samba.
5. Verify original SID, account authentication, file content, peer denial in both directions and the **previously joined Windows pilot's** secure channel/H: without rejoining. Record redacted results. For the .TEST lab run restored-acceptance.py.

The additional official `samba-tool domain backup restore --backup-file=... --targetdir=...` route can alter DC topology/identity and does not restore pupil files. Consult exact installed help and [Samba documentation](https://www.samba.org/samba/docs/current/man-html/samba-tool.8.html); do not substitute it for the full tested same-DC archive or assume client trust has passed.

A failed restore leaves restore-in-progress; do not rerun blindly. Keep diagnostics, abandon only the disposable recovery VDI, and retry on another empty one from an intact backup.

For cutover ensure original is OFF, address is free, and LAN values are approved. Change config to mode=lan/confirmed=true and correct wired bridge. Provision deliberately rejects mode mismatch after installing config and stopping Samba. Through SSH run cutover.py and its exact confirmation, halt, then `vagrant up server --provision`. If NIC topology is not rebuilt correctly, recreate only the disposable VM with guarded destroy and reattach restored VDI. Keep hostname/IP unchanged; validate DNS/trust from LAN before pupils return. Never run two copies of the same DC together.
