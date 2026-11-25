# Backups

Keep three copies on two physical media, one offline/off-site under school policy. The laptop disk and another directory on it are one device. Identify an available USB drive or trusted backup computer before putting real pupil data on this server.

Run `sudo /usr/local/lib/classroom/backup.sh` in the guest. It locks out concurrent jobs, stops Samba, creates an official offline AD backup and complete cold `state.tar`, preserves NT security xattrs, POSIX ACLs and numeric owners, records package versions/checksums, then restarts Samba even on failure. Only a successful set has COMPLETE. The cold archive includes domain identity, account and machine secrets, idmap, SYSVOL/GPOs, configuration and pupil files in the same downtime window. Never copy live LDB/TDB files. [Samba's official backup command](https://www.samba.org/samba/docs/current/man-html/samba-tool.8.html) supplies database locking; its AD-only archive does not include pupil files.

Default output `/var/tmp/classroom-backups/TIMESTAMP` is root-only and on the **disposable OS disk**: export promptly, because destroy deletes it. Backups contain password hashes and private files. SHA256 detects corruption, not malicious replacement; protect the storage.

For export install GnuPG if necessary, package the set and encrypt using its hidden interactive passphrase prompt:

```bash
sudo -i
tar -C /var/tmp/classroom-backups -cpf /root/classroom-backup.tar TIMESTAMP
gpg --symmetric --cipher-algo AES256 --output /home/vagrant/classroom-backup.tar.gpg /root/classroom-backup.tar
chown vagrant:vagrant /home/vagrant/classroom-backup.tar.gpg
chmod 600 /home/vagrant/classroom-backup.tar.gpg
rm /root/classroom-backup.tar
exit
```

Use host OpenSSH scp/SFTP with details from `vagrant ssh-config server` to copy the encrypted file. Do not use Windows PowerShell 5 text redirection for binary exports. Keep temporary SSH config/private keys outside Git, compare source/destination checksums, and disconnect offline media. Keep the encryption passphrase separately in a password manager. Never pass a passphrase via CLI/environment/task configuration.

After baseline restore passes, schedule daily after-class jobs allowing service downtime, sufficient staging space, error monitoring and off-host encrypted export. No plaintext host share is created automatically. Retain daily/weekly/monthly sets within school policy/capacity; never auto-delete the last known-good set. Test restoration after package upgrades and periodically. A powered-off copy of the **whole state VDI plus matching OS environment** is useful too; never copy live VDI/snapshot chains. Keep matching package cache/OS disk before updates so the exact-binary cold restore remains possible.
