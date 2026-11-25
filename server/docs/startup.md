# Automatic startup and graceful shutdown

Guest Samba starts through systemd after the persistent mount is available and `domain-ready` exists. A missing disk/mount must cause failure, never boot an accidental empty domain. Chrony provides the guest clock; Windows domain members follow domain time. Verify clock agreement and NTP before rollout.

The supplied `host/Register-Startup.ps1` registers a current-user Windows logon task running `vagrant up server --no-provision`. Run with `-WhatIf` to review, then deliberately register it. It uses no stored password, no pupil startup and no startup provisioning. Check the actual Vagrant path (`C:/HashiCorp/Vagrant/bin/vagrant.exe` may be used by the installer), Task Scheduler task result/history and guest service health. The user must log into Windows after a reboot; until then the server is unavailable. Start before pupils arrive.

For unattended boot without teacher login, use a separately reviewed Task Scheduler service account that owns the VirtualBox machine/Vagrant home, least-privilege credentials and 'Run whether user is logged on or not'. Switching to SYSTEM cannot simply see a user's registered VM. This is not configured automatically. A dedicated Linux host is a better fit if service must exist before login.

Review host sleep/lid settings on AC power, plug into reliable power, and schedule Windows updates outside lessons. No power policy or reboot is changed automatically. Do not disable Windows updates. The laptop still works as a workstation, but closing the lid must not unexpectedly stop the classroom. Test the selected policy with approval.

Before host shutdown, VM recreation, unplugging storage or migration, run `vagrant halt server` and wait for poweroff. Never terminate VirtualBox or suspend the host as a backup method. `vagrant up server --no-provision` resumes normal service. Keep `vagrant suspend` out of migration/backup workflows.
