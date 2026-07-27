# Session Memory (auto-updated by Opus, max 2000 chars)

## Session Facts

- T480 OpenRC scans ALL of /etc/init.d/ for LSB `# Provides:` — a stray backup script with the same Provides name creates a provider collision, so OpenRC starts NONE of the rivals at boot (silently; not even shown as "stopped" in `rc-status`). `/run/openrc/deptree` is the authoritative diagnostic (grep the service name; want exactly one provider).
- `rc-service <name> start` resolves by FILENAME, bypassing provider resolution — so it succeeds by hand even when boot fails. This false-positive is why guix-daemon was "fixed" repeatedly yet dead every reboot; the in-place `cp file file.backup-$(date)` reflex WAS the bug.
- Fix pattern: move stray backups OUT of /etc/init.d (e.g. /var/backups/), then `sudo rc-update -u`; verify `rc-status default` lists the service `[started]`. T480 guix-daemon fixed this way 2026-07-27.
- Never leave timestamped backups inside init-scanned dirs (/etc/init.d OpenRC, /etc/rc*.d sysv).

## User Model (max 1500 chars for this section)

- Opens with clear scope ("a number of things to fix today") but mixes true instructions with question-shaped items (kitty scroll "is it sane?") — treat questions as questions, don't edit.
- Wants ROOT cause, not another manual restart: "how come no one can fix it?" = fix it permanently + explain the mechanism.
- Values live-probe-before-theorise and being told plainly when a prior note/theory was wrong.
