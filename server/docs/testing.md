# Acceptance gates: one server and one Windows pupil VM

Never run these destructive/recovery exercises on production storage. Use the isolated .TEST lab. No extra pupil fleet is created. A recovery server replaces the lab server **sequentially**, not as a second running DC.

## Server and two-account tests

1. Create new lab state, provision, and interactively create the domain. Run verify.sh, record package versions and SID. Copy `tests/lab-acceptance.py` into the guest via scp/SFTP and run as root. It creates only labalice/labbob, private NT ACLs and distinct marker files. Random credentials remain root-only, not logs/argv. It authenticates both accounts, verifies own read/write and peer read/write denial in both directions.
2. Run `vagrant provision server` twice. Re-run verify.sh and copy/run restored-acceptance.py (despite the name it also validates the retained state after reruns). Account passwords, SID, markers and isolation must remain identical.
3. On the Windows pupil VM, join the lab once (approved client reboot). Use the encrypted/backed-up root credentials only through an approved private process; to choose known passwords use accounts.py reset and first-login change. **If passwords are changed, refresh the root-only lab credential record privately before backup** or the password-based restored test will fail. Simpler: finish automated server restore test first, then do Windows tests and a second backup/restore drill for Windows trust.

## Guarded VM recreation

Export a complete backup first. Halt server, note external VDI path/size/hash, then `vagrant destroy server`. The guard must refuse if VM is running or snapshots exist; test refusal before halting. Ensure VDI file remains. `vagrant up server` with initialize_storage=false must reuse the same domain and files; run restored-acceptance.py. The VDI hash naturally changes after boot, so compare an offline before/after-destroy hash **before** restarting, not after.

## Full backup restoration onto empty storage

1. Run backup.sh and export the full COMPLETE set securely. Record original SID, original file hashes and both account authentication/isolation results.
2. Halt and guarded-destroy only the disposable lab server VM. Preserve its original state VDI unchanged as rollback. Set a separate config/new VDI path, same lab realm/domain/hostname/IP/netmask, create new empty VDI, initialize/provision empty server. Set initialize flag false. **Do not create a new domain.**
3. Copy backup into root-only guest storage and run restore.sh as described in restoration.md. Run verify.sh, restored-acceptance.py, and inspect SYSVOL ACLs. Original accounts/passwords/SID and markers must survive; peer reads and writes must be denied. Capture no passwords.
4. Corruption/rejection tests: modified state.tar must fail its checksum before writing; nonempty destination must refuse; mismatched domain/IP and versions must refuse. Use expendable copies/disks, not original backups.
5. Keep the pupil VM joined before the second restore drill. After restoration, `Test-ComputerSecureChannel` must pass **without rejoining**. Test Alice/Bob login, H: mapping, saved markers, fresh own write/read and explicit peer UNC denial. Rejoining would hide a failed trust restore and does not count as passing.

## Windows pilot checklist

| Check | Required result |
| --- | --- |
| Edition/join/DNS/time | Windows Pro/Enterprise, lab domain join, DC-only DNS, accurate clock |
| Alice then Bob | Both log in as standard users; neither in local Administrators |
| H: | Correct personal UNC on both logins; save/read survives logoff/restart |
| Privacy | Explicit other-user UNC read/write fails both ways |
| Same identity on different PC | After VM pilot, verify on first physical PC before remaining ten |
| Restored domain | Existing machine secure channel/login/H: pass without rejoin |
| Host service behavior | Approved power/startup test keeps teacher Windows usable |

Run static checks locally with `powershell -File host/Validate-Project.ps1`; these validate syntax/config/doc structure only. Record actual runtime evidence in validation.md. No classroom rollout until server restoration and Windows pilot pass.
