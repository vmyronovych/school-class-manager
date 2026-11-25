# School Class Manager

## Reproducible classroom infrastructure

The current classroom server project is in **[server/](server/README.md)**: Vagrant + VirtualBox + Ubuntu Samba Active Directory, persistent domain/pupil storage, safe provisioning and recovery tooling. It provisions one server and optionally one Windows pupil test VM; the 11 classroom clients remain physical PCs.

Start with its [prerequisites and deployment guide](server/README.md), [test/restore plan](server/docs/testing.md), and [actual validation status](server/docs/validation.md). A real domain/address must be confirmed before creation; no host/router network settings or reboots are automated without approval.

The application/Raspberry Pi description below is the pre-existing, separate application plan. Its manually completed Pi infrastructure status does not mean this Vagrant server or restoration has been tested.

## Existing application project

Web app for a school computer classroom running on the classroom's own Raspberry Pi 4 (Samba AD DC). Teachers open `https://dc1.ad.school.lan` from any classroom PC, sign in with their domain account and manage student accounts, handouts, submitted work and server health — no SSH, no RSAT.

- Backend: ASP.NET Core 8 (Kestrel) on `linux-arm64`, talks to Samba locally (`samba-tool` via a sudo wrapper, LDAP over `ldapi://`, `/srv/data` via `System.IO`).
- Frontend: React 18 + TypeScript + Ant Design 5, served as static files by Kestrel.
- Runs as a single systemd service; updates are a tar.gz from GitHub Releases.

## Documents

| File | What |
| --- | --- |
| `docs/plan.md` | Development plan: scope, architecture, API, security, repo layout, milestones M0–M6, tests, risks, decisions |
| `docs/deployment.md` | Classroom infrastructure guide (Ukrainian): Pi, Samba AD DC, shares, snapshots, GPO, imaging |
| `docs/mockups.md` | Screen mockups and antd component map |
| `CLAUDE.md` | Working rules for Claude Code sessions |
| `pi/` | Files that live on the Pi: systemd units, sudoers, wrappers, TLS scripts, `install.sh` |

## Status

Pre-code. Milestone M0 (infrastructure) is done by hand from `docs/deployment.md`; M1 starts with the solution skeleton (see `docs/plan.md` → «Порядок усередині M1»).

## License

MIT — see `LICENSE`.
