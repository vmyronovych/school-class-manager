# Reproducible classroom server

One Ubuntu Samba AD domain controller/file server, plus **one optional Windows pupil test VM**. The 11 classroom PCs remain physical Windows Pro clients. The teacher host remains a Windows workstation. The existing application and Raspberry Pi instructions elsewhere in this repository are separate; this project does not install the web application.

## Evaluation and limits

Samba AD supplies a single domain identity for login on any joined PC; an account's H: points to its private server folder. Local Windows profiles are separate per PC. Desktop/Documents are not automatically roaming: save classroom work to H:, or configure Folder Redirection later after a separate pilot. Do not enable roaming profiles by default.

4 GiB RAM and 2 vCPUs is a reasonable starting allocation for 11 clients; actual simultaneous file workloads must be measured. The verified host is an i5-6300U, 17,066,356,736 bytes RAM (15.9 GiB), virtualization enabled with SLAT, and about 182 GiB disk free on 2026-10-05. Wi-Fi is connected at 192.168.0.174/24 with gateway 192.168.0.1; Ethernet is disconnected. These are observations, **not approved classroom addresses**.

The server stops when the laptop sleeps, loses power, travels, or Windows restarts. Wired Ethernet is strongly preferred: [VirtualBox's wireless bridge rewrites MAC addresses](https://docs.oracle.com/en/virtualization/virtualbox/6.0/user/network_bridged.html), and the AP/driver can prevent reliable service. A single DC/file server is a budget compromise with one failure point. Administrators can read pupil data; pupils and ordinary teacher accounts cannot read others' folders. This is not encryption against the host owner.

The requested stack is retained. Samba and VirtualBox base are open source; the Extension Pack is unnecessary and has different terms. [Current Vagrant uses BUSL](https://github.com/hashicorp/vagrant/blob/main/LICENSE), so this is free for classroom use but not an entirely open-source stack. A spare, always-on Linux host with Samba and KVM/libvirt is the better fully open-source option for dependable service. A Linux guest under Windows Hyper-V avoids VirtualBox drivers but requires another provider/image workflow and host feature changes. No stack switch is made here.

[Windows 10 Pro standard support ended on 2025-10-14](https://learn.microsoft.com/en-us/lifecycle/products/windows-10-home-and-pro). Domain joining still works, but the school must plan supported clients or applicable ESU coverage.

## Dependencies and prerequisites

Pinned host versions: **Vagrant 2.4.9**, **VirtualBox 7.2.20** base only; no plugins. Guest: **bento/ubuntu-24.04 202510.26.0 amd64**, Ubuntu 24.04 LTS. [HashiCorp's tutorial uses this box version](https://developer.hashicorp.com/vagrant/tutorials/get-started/setup-project). Ubuntu security packages deliberately track noble, noble-updates and noble-security rather than freezing vulnerable Samba packages. `/srv/classroom/packages.lock` and every backup record exact resolved versions. Keep the downloaded box and matching packages/OS image for offline restoration; validate upgrades and new pins in the lab first. Reproducible configuration is not a promise of bit-identical apt packages over time.

Dependencies are machine-readable in [dependencies.json](dependencies.json). Download installers only from [HashiCorp](https://releases.hashicorp.com/vagrant/2.4.9/) and [Oracle](https://download.virtualbox.org/virtualbox/7.2.20/); compare SHA256 with their published manifests and verify Authenticode publisher signatures. Known Windows hashes:

The checked-in [box-metadata.json](box-metadata.json) pins the downloaded amd64 box's SHA256. This is a locally observed integrity pin, not an independently signed publisher digest (registry metadata supplies no checksum). The downloaded OVF was inspected: SATA Controller has its OS at port 0 and free port 1 for persistent state. Archive/cache this exact artifact for recovery; review rather than silently accept any future checksum change.

| File | SHA256 |
| --- | --- |
| vagrant_2.4.9_windows_amd64.msi | `3bdd967927705872a70c7c98e0576afd5acd9dd73b527695f4d9dd75dd26cbe3` |
| VirtualBox-7.2.20-175154-Win.exe | `a81777d2b36380ce042a29e9c554cf032eb46a793f62e3cc82e7411e535c2c26` |

Install during an approved maintenance window: VirtualBox installs networking drivers and can disconnect the host. Never reboot automatically. If an installer requires a reboot, save work and ask before doing it. Do not disable Hyper-V, VBS or security settings automatically. A Windows Pro or Enterprise ISO and valid licensing/evaluation terms are needed for the pupil VM; no Windows image is redistributed here.

Plan storage outside the checkout, e.g. `C:/ClassroomState/lab-state.vdi` for test and a **different** `C:/ClassroomState/production-state.vdi` for real data. Start at 64 GiB dynamically allocated; keep room for OS/box, Windows test VM, backup staging and restoration. Never rely on a backup on the same physical disk. Secure the host account and VDI directory with NTFS permissions; BitLocker is useful if already available. Vagrant SSH is effectively root access: protect `.vagrant` and the teacher account.

## Safe deployment sequence

Run from `server/` in PowerShell:

```powershell
Copy-Item config.example.json config.local.json
# Edit config.local.json. Keep mode=lab and .TEST domain for isolated testing.
powershell -NoProfile -ExecutionPolicy Bypass -File .\host\New-StateDisk.ps1
# Only for the explicitly new empty disk: set initialize_storage=true.
vagrant validate
vagrant up server
# Set initialize_storage=false after the first successful provision.
vagrant ssh server
```

Provisioning formats only an explicitly approved empty, unpartitioned, correctly sized `/dev/sdb`; it refuses any recognized unexpected filesystem/signature. It does not create a domain, reset passwords or wipe existing data. The external state VDI is required before `up`. On the guest:

The PowerShell example permits the reviewed script in that child process only; it does not change the machine/user execution policy. Use the same invocation pattern for other supplied host scripts if the default policy prevents running them.

```bash
sudo /usr/local/lib/classroom/domain.py create
# Type the displayed realm/IP confirmation; passwords are interactive and hidden.
sudo /usr/local/lib/classroom/verify.sh
```

Never pass a domain password to a CLI option, environment variable, JSON file, terminal transcript or Vagrant provisioner. Do not enable `set -x`, `VAGRANT_LOG=debug` or session recording around secrets. Protect backups: they contain password hashes, machine secrets and pupil files. Secret inputs remain in memory; Samba's domain secrets are necessarily persisted inside the private protected domain database.

Rerun `vagrant provision server`; existing identity must match and the domain must remain intact. Changes to realm, short name, hostname or IP are rejected once disk identity is recorded. Failed partial domain creation is blocked for manual recovery; never rerun it over the partial directory. Take a backup before changing packages/configuration.

## Real LAN deployment gate

Before creating a real domain, explicitly confirm with the owner: domain DNS name (prefer a subdomain of a school-owned name; avoid `.local`), NetBIOS name, server hostname, static IP/prefix, gateway, upstream DNS, wired bridge adapter and reserved DHCP exclusion. The default `.TEST` realm is lab-only. Use a **new configuration and separate production VDI**; do not rename the test domain into production.

Set `mode=lan`, `confirmed=true` only after confirmation. See [networking.md](docs/networking.md). Bridged NIC 2 makes the server reachable on the LAN; NAT NIC 1 supplies management/update access and is excluded from Samba binding. NAT port forwarding alone is not an AD deployment. Host DNS and router configuration are never changed by `vagrant up`.

## Verification and rollout

Follow [testing.md](docs/testing.md): two accounts, own-folder write/read, denied peer read/write, provisioning rerun, full backup/restore onto empty storage, persistent-disk survival through VM recreation, and one Windows Pro client login/H:/trust test. **Do not roll out to the other 10 clients until every gate passes.** See [validation.md](docs/validation.md) for checks actually performed versus pending checks; static checks do not establish a working domain or tested restoration.

## Operations

| Guide | Purpose |
| --- | --- |
| [Windows joining](docs/windows-client.md) | One test VM first; physical PCs later |
| [Accounts](docs/accounts.md) | Pupil, teacher and separate administrative identities |
| [H: drives](docs/home-drives.md) | Shared identity/private files without roaming profiles |
| [Startup](docs/startup.md) | Guest startup and Windows host logon task |
| [Backups](docs/backups.md) | Consistent cold backups, encryption, off-host copies |
| [Restoration](docs/restoration.md) | Preserve existing SID/accounts/files, no new domain |
| [Migration](docs/migration.md) | Move safely to another host |
| [Troubleshooting](docs/troubleshooting.md) | DNS, time, permissions, storage and virtualization |

## Exactly what destroy deletes

`vagrant halt server` then `vagrant destroy server` invokes a mandatory guard which refuses a running/suspended VM or snapshots, checks the attached disk, and detaches SATA port 1 before VirtualBox unregisters/deletes the VM. It deletes the server VM definition and **disposable OS disk** (packages, guest `/etc` not on state, temporary files, staging under `/var/tmp`, journals, and backups left there). It does **not** delete the detached external state VDI, its domain/accounts/SYSVOL/private files, exported backups or the box cache. `.vagrant` machine state is removed/updated by Vagrant. `vagrant destroy pupil` deletes the pupil VM and its whole Windows OS/local profile disk; the source ISO remains.

Do not use unqualified `vagrant destroy` during testing: specify the machine. Do not bypass the trigger with GUI deletion, `VBoxManage unregistervm --delete`, or snapshots; those can delete an attached persistent VDI. Reattaching the old VDI and provisioning rebuilds the OS around the **existing** domain. Using a new empty VDI prepares an empty server; creating a new domain then creates a **new SID**, even with the same names, and cannot recover existing Windows trust/ACL identities. State on one disk is persistence, not a backup.
