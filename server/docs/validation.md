# Validation evidence

Date: 2026-10-05. Host inspection was read-only; no host/router/client networking or reboot was performed.

| Check | Status/evidence |
| --- | --- |
| Hardware | i5-6300U; 17,066,356,736 bytes RAM (15.9 GiB); virtualization firmware, SLAT and VM monitor extensions True; HypervisorPresent False |
| Storage/network | 195,353,231,360 bytes initially free; Wi-Fi 192.168.0.174/24, gateway 192.168.0.1; wired Ethernet disconnected |
| Installed VM tools | Vagrant/VirtualBox not found in PATH or standard install locations |
| Dependency downloads | Vagrant 2.4.9 MSI downloaded; SHA256 matches official manifest. VirtualBox 7.2.20 Windows hash read from official manifest |
| Local static checks | PASS: 9 mocked storage-safety regression tests; 10 evaluated Vagrant DSL configuration/scope cases; PowerShell, Bash, Python and Ruby syntax; safe example defaults |
| Local tooling | Used Git Bash, portable Python 3.12.10 and portable Ruby 4.0.7 for checks; no VM/network drivers installed. PowerShell validator ran with process-only execution policy override |
| Base box inspected | Downloaded 651,326,766-byte pinned amd64 box; observed SHA256 `14ae82e423c270d1c03907faf90691b0fbd673b16bfc369a949808e4e6991b82`; OVF confirms SATA Controller, OS port 0, free state port 1 |
| VM provisioning/rerun | NOT RUN: VM prerequisites unavailable |
| Two-account Samba isolation | NOT RUN: executable lab test provided |
| Backup restoration on empty disk | NOT RUN: executable backup/restore and acceptance tests provided |
| Disk survives Vagrant destroy | NOT RUN: detach guard implemented, runtime verification required |
| Windows pupil login/H:/trust | NOT RUN: licensed/evaluation ISO and VM tools required |
| Real LAN/domain | NOT PROVISIONED: owner confirmation of domain/addressing pending |

An attempted msiexec administrative extraction of Vagrant was rejected by automatic approval review without a detailed reason. No installer was executed successfully. VirtualBox install remains pending explicit permission because network driver installation may interrupt Wi-Fi. Do not treat static checks or this project's existence as a passed restoration/pilot gate.
