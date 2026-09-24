# School Class Manager

Web app for a school computer classroom running on the classroom's own Raspberry Pi 4 (Samba AD DC). Teachers open `https://dc1.ad.school.lan` from any classroom PC, sign in with their domain account and manage student accounts, handouts, submitted work and server health — no SSH, no RSAT.

- Backend: ASP.NET Core 8 (Kestrel) on `linux-arm64`, talks to Samba locally (`samba-tool` via a sudo wrapper, LDAP over `ldap://127.0.0.1`, `/srv/data` via `System.IO`).
- Frontend: React 18 + TypeScript + Ant Design 5, served as static files by Kestrel.
- Runs as a single systemd service; updates are a tar.gz from GitHub Releases.

## Documents

| File | What |
| --- | --- |
| `docs/plan.md` | Development plan: scope, architecture, API, security, repo layout, milestones M0–M6, tests, risks, decisions |
| `docs/deployment.md` | Classroom infrastructure guide (Ukrainian): Pi, Samba AD DC, shares, snapshots, GPO, imaging |
| `docs/mockups.md` | Screen mockups and antd component map |
| `CLAUDE.md` | Working rules for Claude Code sessions |
| `pi/` | Files that live on the Pi: systemd units, sudoers, wrappers, TLS scripts, `install.sh`, GPO logon script |
| `tools/pi-fixtures/` | Real command outputs from the Pi for parser tests |

## Status

Milestone M1 in progress: sessions 1, 2 and 2a are done (solution skeleton, `/healthz`, SPA layout on mockup data, CI, `SudoRunner` and wrapper tests, student login format `ivanenko.petro.2011` and school-year classes `2025-4a`). Milestone M0 (infrastructure) is done by hand from `docs/deployment.md`. See `docs/plan.md` → «Порядок усередині M1» and `CLAUDE.md` → «Стан».

## License

MIT — see `LICENSE`.
