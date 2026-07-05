---
name: dotcortex-borg
description: Operate the dotcortex-borg versioned encrypted backup — endpoints, verbs, secret provisioning, and the legacy-backup preservation law.
model: claude-sonnet-5
---

# dotcortex-borg — Versioned Encrypted DotCortex Backup

Borg sibling of HelmCortex's `helmcortex-borg`. Source: `backup.org` → tangles to `x230/.local/bin/dotcortex-borg` (X230 is the writer).

## Endpoints (one repo each, repokey-blake2)

| Endpoint | Repo |
|----------|------|
| `secret-ssd` | `/mnt/secret-ssd/Borg/DotCortex` (canary+UUID guarded) |
| `t480s` | `t480s:Borg/DotCortex` (T480s local disk) |

## Verbs

`init` · `create [--dry-run]` · `prune` · `check` · `list` · `status`

## Scope

ALL of `~/DotCortex` — `.git`, untracked local state, overlays. Only `nohup.out` runtime junk excluded. Retention: 48h all, 14 daily, 8 weekly, 12 monthly.

## Secrets

- Passphrases: `~/.config/dotcortex-borg/{endpoint}.pass`, provisioned via `helmstow` from `NEXUS/stow/` — NEVER tangled here; DotCortex is public
- Key exports: `init` writes to `~/.local/state/dotcortex-borg/key-{endpoint}.txt` — move to `HelmCortex/NEXUS/keys/borg/`
- Borg binary: Guix core profile (`~/.guix-extra-profiles/core/core/bin`)

## HARD RULE — Legacy backups are sacred

**Never delete or overwrite the old DotCortex rsync backups on the ironwolf drives.** They contain unique files stripped from the repo history that are not tracked anywhere else. The borg lane complements them; it does not supersede them.

## Future

Other `backup.org` rsync scripts (backup-system, backup-nextcloud, backup-games, backup-retropie) may migrate to borg lanes bit by bit — evaluate each on its own merits; some may not suit borg.
