# Pupil, teacher and administrative accounts

Inside `vagrant ssh server`, use the root-only wrapper:

```bash
sudo /usr/local/lib/classroom/accounts.py create alice --role pupil
sudo /usr/local/lib/classroom/accounts.py create teacher --role teacher
sudo /usr/local/lib/classroom/accounts.py create teacheradmin --role admin
sudo /usr/local/lib/classroom/accounts.py list
sudo /usr/local/lib/classroom/accounts.py reset alice
sudo /usr/local/lib/classroom/accounts.py disable alice
sudo /usr/local/lib/classroom/accounts.py enable alice
```

Create prompts for hidden passwords, requires 14+ characters, and forces a password change at first interactive login. Existing names/folders are refused; reruns do not reset an account or replace its ACL. Pupils belong to Pupils and default Domain Users only. Teachers belong to Teachers and default Domain Users only. The separate maintenance identity belongs to Domain Admins and has access to pupil folders. Ordinary teacher accounts receive no broad pupil-file permissions or account delegation; use `teacheradmin` for deliberate management. Never make an entire teacher group Domain Admins.

The account tool must run locally as root; pupils/ordinary teachers cannot use it. Vagrant/SSH control is restricted to the trusted host owner. There is no claim that the existing unfinished management app is deployed here.

Disabling retains all files and SID. Resetting retains account/SID and files; a new temporary password must change on next login. Do not delete/recreate a login to reset a password: the new SID will not own the original permissions. Deletion and bulk CSV/password imports are intentionally not automated. When a pupil leaves, disable, archive according to school policy, then delete only after explicit review. Use a password manager for administrator credentials and a private, approved method to deliver pupil credentials.

The two lab acceptance accounts have random temporary credentials saved root-only on the state disk for restoration authentication tests. After the automated restoration test, use `accounts.py reset labalice` and `reset labbob` to choose known temporary credentials for Windows testing. Never print or commit the lab credentials file.
