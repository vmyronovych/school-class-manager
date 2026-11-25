# One pupil test VM, then physical Windows Pro clients

Use licensed Windows 10 Pro media to match the classroom, or official Microsoft Windows Enterprise evaluation media under its terms. Home edition cannot join AD. Do not download unofficial Vagrant Windows boxes. This project defines **one** optional pupil VM; no set of 11 pupil VMs is created.

Set `pupil_iso` to an absolute local ISO path and `pupil_iso_sha256` to the verified publisher checksum. `vagrant up pupil --no-provision` opens VirtualBox's Windows installer. The pinned Linux base is used solely to supply a disposable VM disk/controller; choose Custom installation and replace all partitions on **the pupil VM's disk only**. Install Pro, complete setup, choose a unique computer name such as LAB-PC01 and a local administrator password entered interactively. The VM has no Vagrant Windows communicator or automatic password-bearing unattended file. After install, halt the pupil and eject ISO in VirtualBox or set boot order to disk; keep the ISO configured for reproducible reinstall. Never attach the server state disk to pupil.

Inside Windows, identify NICs using `Get-NetAdapter`. Disable the NAT NIC in the **test VM only**. Set the internal-network NIC to 192.168.77.20/24, no default gateway, DNS 192.168.77.10. If lab subnet was changed, use corresponding values. GUI network changes here affect only the test VM. Confirm Pro edition and DNS SRV lookups. The test VM does not need classroom LAN access.

Keep a working local admin (`.\localadmin`) and its recovery password before any join. Back up needed local files; domain login creates a different local profile. Do not delete local profiles or disable the local admin during the pilot.

Copy `host/Join-Classroom.ps1` to the pilot client. In elevated PowerShell, run it with the confirmed values (or use System Properties → Computer Name → Change → Domain):

```powershell
.\Join-Classroom.ps1 -Domain AD.CLASSROOM.TEST -ServerIP 192.168.77.10 -InterfaceAlias 'Ethernet 2' -ComputerName LAB-PC01
```

The script asks before changing client DNS/joining, saves prior DNS in `%ProgramData%\Classroom-dns-before.json`, prompts for a domain administrator credential, and **does not restart**. For physical PCs, obtain approval for DNS changes and the required client reboot. Save work, then restart only when authorized. Use domain Administrator just for joining, then use a separate pupil login such as `CLASSROOM\labalice`.

Check `whoami`, `Test-ComputerSecureChannel`, `nltest /dsgetdc:AD.CLASSROOM.TEST`, `net use`, and H:. Test Alice then Bob, close all sessions between users, and confirm peer read/write denial using the guide. The Windows local Administrators group must not contain Domain Users or Pupils. Ordinary teachers are not Domain Admins. Domain Admins have elevated rights on member PCs: use that separate account only for maintenance.

After restoration, repeat secure-channel verification on the **same joined pilot** without rejoining. A required rejoin means the restore/trust acceptance gate failed and must be investigated. When moving to physical clients, join one first and log the result before the remaining ten.

If joining fails, restore DNS from the saved snapshot (or `Set-DnsClientServerAddress -ResetServerAddresses` only if the previous setting was DHCP), keep local admin access, and fix DNS/time rather than reinstalling/rejoining repeatedly. Leaving a domain and rebooting also needs explicit approval.
