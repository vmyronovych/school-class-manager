# Troubleshooting

| Problem | Safe checks |
| --- | --- |
| Tools missing | Install pinned versions in approved maintenance window; verify actual paths. No plugins/Extension Pack. |
| VM won't boot | Check BIOS virtualization, VirtualBox logs and Hyper-V/VBS coexistence. Do not disable security/reboot automatically. |
| Disk absent/format refused | Verify absolute path, port 1, expected size/signatures. Never wipe an unknown disk to fix it. |
| Identity mismatch | Use original config/state pair; only explicit topology transitions use cutover.py. |
| Samba failure | journalctl -u samba-ad-dc; findmnt /srv/classroom and /var/lib/samba; smb.conf link; domain-ready/database consistency. Partial domain means recovery, not reprovisioning. |
| DNS bind failure | ss -lntup; resolved status; correct NIC/IP. Do not expose Samba on NAT as a shortcut. |
| LAN inaccessible | Wired bridged NIC 2, cable/subnet, AP isolation, host bridge driver/router rules. NAT alone is insufficient. |
| Join/Kerberos failure | DC-only client DNS, SRV records, SMB/RPC ports, Pro edition, unique computer name and time within five minutes. |
| H: missing | Home attributes, net use, direct UNC, network at logon, cached login while DC is off. |
| Own files denied | Account SID and `samba-tool ntacl get PATH --use-s3fs --service=pupils`; restored xattrs. Never grant Everyone Full Control. |
| Peer files accessible | Stop rollout; review owner/DACL/inheritance and cached SMB sessions. Recheck both directions. |
| Backup failure | Free space, COMPLETE/hash manifest, exported good set and restarted Samba. |
| Restore versions differ | Recover matching OS/packages or separately review official isolated recovery. Do not bypass compatibility guard. |
| Restored trust broken | Check SID, machine-password backup age, DNS/time. Rejoining does not prove restoration succeeded. |

Collect redacted versions, VM/mount/service status and errors. Do not collect passwords, auth files, private domain DBs, raw backups or debug transcripts as ordinary diagnostics.
