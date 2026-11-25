# Move to another host

Install pinned Vagrant/VirtualBox on the new Windows host during an approved network/reboot window. Check virtualization, RAM/disk space, wired bridge and power policy. Copy repository/configuration; keep teacher workstation files separate.

Make/export/test a full backup, halt server and pupil, verify poweroff/no snapshots, then copy the **powered-off external state VDI** through protected/encrypted media. Compare SHA256 at both ends. Preserve original untouched/offline. Never run original and copied DC simultaneously.

Use the same realm/domain/hostname/IP/netmask and sizing; change only state path and actual wired adapter. Set initialize_storage=false. `vagrant up server` reattaches old state and rebuilds OS/packages/mounts around it. It must not create a domain. Match the tested package baseline and validate any upgrade separately.

Keep router IP exclusion; update any MAC filtering/reservation because VM recreation may change MAC. Check DNS SRV, NTP, private files and the pilot's secure channel without rejoining. Register startup for the new teacher account/project path and disable old startup before cutover.

If state is damaged, use full isolated restoration first. Rollback requires stopping the new DC and bringing only the old copy back; old copies are stale, so preserve pupils' post-migration work before rollback. Retain old VDI/backups through an agreed validation period.
