---
name: dotcortex-gotchas
description: Troubleshooting DotCortex issues — stow conflicts, tangle failures, Guix installer problems, /tmp permissions.
---

# DotCortex Known Gotchas

## Makefile is tangled output — never edit it directly

The Makefile is tangled from `loom.org`. Any direct edits will be overwritten by the next `make tangle`. Always edit the Makefile template block in `loom.org` instead, then re-tangle.

## First tangle fails with "No rule to make target .mk"

The Makefile includes `.mk` fragment files that don't exist until after the first tangle. `INSTALL.sh` handles this by creating empty stubs. If running manually:

```bash
mkdir -p all/.mk
for mk in flatpak guix guix-substitutes snap appimage cargo homebrew npm pip; do
  [ -f "all/.mk/${mk}.mk" ] || touch "all/.mk/${mk}.mk"
done
make tangle
```

## Loom bootstrap (chicken-and-egg)

`loom` needs `~/.config/maak/maak.scm` (placed by stow) and Guix guile. You CANNOT use `loom stow:x230` for the first stow — use `make safe-stow` directly. `INSTALL.sh` handles this by pre-placing `maak.scm` before stow runs.

After the first `make safe-stow`, loom is functional and can be used for all subsequent stow operations.

## Guix emacs not in SSH PATH

On Guix machines, emacs lives at `~/.guix-extra-profiles/core/core/bin/emacs`. NOT in the default SSH PATH. The `.zshenv` (tangled from `shell.org`) sources Guix profiles for ALL zsh invocations including non-interactive SSH. For bash over SSH:

```bash
export PATH="$HOME/.guix-extra-profiles/core/core/bin:$PATH"
```

## "not owned by stow" after repo rename (.dotfiles -> DotCortex)

If the repo was renamed, all old stow symlinks become foreign (pointing to the old path). Stow reports "existing target is not owned by stow" for every file. Remove dangling symlinks first:

```bash
find ~ -maxdepth 5 -lname "*/.dotfiles/*" -not -path "*/.git/*" -delete
```

Then re-stow. The safe-stow target handles this conflict type automatically with its third sed pattern.

## safe-stow handles three stow conflict message formats

Stow has three different conflict message formats across versions and situations:

1. `existing target is neither a link nor a directory: FILE` (stow <2.4)
2. `cannot stow PKG/FILE over existing target FILE since neither...` (stow 2.4+)
3. `existing target is not owned by stow: FILE` (foreign files/symlinks after repo rename)

The safe-stow target matches all three with sed patterns, filters out HelmCortex, backs up real files, removes them, then stows. If stow still fails, it auto-retries with `--ignore=HelmCortex`.

## "unknown package" for packages that definitely exist — stale guix binary, not channels

If `guix show <pkg>` or a manifest apply rejects packages that demonstrably exist (fastfetch, deskflow, borg at an ancient version), check WHICH guix answered before touching the manifest:

```bash
type -a guix          # fossil: /usr/local/bin/guix (bootstrap seed, frozen at install version)
ls -la ~/.config/guix/current   # per-user current — the real one after guix pull
~/.config/guix/current/bin/guix --version
```

Root cause chain: if the `~/.config/guix/current` symlink is broken or missing, the `.zshenv` `[ -d ... ]` guard silently skips the PATH prepend and every shell — including loom's clean-guix-env wrapper — falls through to the 1.4.0 fossil. The error then looks exactly like channel drift. Fix: `loom guix:pull` (recreates the symlink), then re-validate with the explicit current path before commenting anything out of a manifest. Never gut a manifest on the fossil's testimony (X230, 2026-06-10).

## Guix installer fails on non-interactive terminal

The official `guix-install.sh` requires interactive stdin. If running via SSH, CI, or piped input, use the manual install method documented in `INSTALL.sh`.

## Guix installer fails with "Missing commands: daemonize"

On Devuan/sysv-init systems, install `daemonize` first: `sudo apt install daemonize`

## Guix ftpmirror SSL errors

The `ftpmirror.gnu.org` redirector sometimes sends you to mirrors with broken SSL certificates. Use `ftp.gnu.org` directly:

```bash
wget https://ftp.gnu.org/gnu/guix/guix-binary-1.5.0.x86_64-linux.tar.xz
```

## LD_PRELOAD libgtk3-nocsd warning

On systems with `libgtk3-nocsd` in `LD_PRELOAD`, Guix commands emit a harmless warning. Ignore it or `unset LD_PRELOAD`.

## Absolute symlinks in overlay dirs abort stow

If an org file tangles an absolute symlink (e.g. `.config/guix/current -> /var/guix/...`), stow will refuse to manage it. Remove such symlinks from overlay dirs before stowing — they are machine-specific. `INSTALL.sh` auto-cleans these.

## /tmp permissions break tangle AND guix pull

If `/tmp` has restrictive permissions (e.g. `755` instead of `1777`), two things break:

1. **Tangle**: emacs `org-persist` can't create temp directories
2. **Guix pull/build**: sandbox can't bind-mount

Fix: `sudo chmod 1777 /tmp`. Tangle-only workaround: `TMPDIR=~/.cache/tmp make tangle`

## pipefail interaction with grep -v

Under `set -euo pipefail`, `grep -v PATTERN` returns exit code 1 when it filters ALL lines. Kills the pipeline. Always wrap: `{ grep -v PATTERN || true; }`

## Guix substituter display bug

`guix package` occasionally crashes with `Wrong type argument in position 1: #f` during substitute download progress display. Cosmetic — retry the command.

## Guix python3 shadows distro tooling via env shebangs

The Guix core profile ships `python3` ahead of `/usr/bin` in PATH, so every `#!/usr/bin/env python3` shebang in distro tools (e.g. Vendefoul Wolf's `gksu`) resolves to Guix Python — which lacks `_tkinter` and crashes with `ModuleNotFoundError`. Fix is declarative, not OS patches: `debian/.local/bin/python3` (tangled from `guix.org`) execs `/usr/bin/python3`; `~/.local/bin` precedes the Guix profile in PATH so shells, env-shebangs, and GUI subprocesses all get the distro interpreter. Guix-built apps are unaffected — they reference their interpreter by absolute `/gnu/store/...` path, never through PATH. Guix Python stays reachable at `~/.guix-extra-profiles/core/core/bin/python3` (T480, 2026-06-10).

Related red herring: a session-stale `GUIX_PYTHONPATH` (e.g. `python3.11` site-packages under a `python3.12` profile) looks like a broken profile but is just login env predating a profile rebuild. Check the profile's own `etc/profile` before "fixing" anything — re-login/reboot resolves it.

## /model and /config write into the stowed settings.json

`~/.claude/settings.json` is a stow symlink into `all/.claude/settings.json`, so harness commands that persist defaults (`/model`, `/config`, theme changes) dirty the tracked DotCortex worktree directly. Don't commit the tangled file alone — backport the new keys into the settings block in `hooks.org`, re-tangle, and commit both together (T480, 2026-06-10).

## ssh ConnectTimeout does NOT bound a hung remote command (mux-session picker hang)

`ssh -o ConnectTimeout=N -o ConnectionAttempts=1` only bounds the TCP/auth handshake. Once the connection succeeds, a remote command that hangs blocks the local `ssh` forever — `ConnectTimeout` never fires. This bit `mux-session`: `build_menu` probes every fleet host sequentially (`tmux`/`zellij`/`wsl.exe ... tmux list-sessions`) before drawing the fzf picker, so one wedged probe meant the picker never rendered. Intermittent because it only bit when a Windows host (gillean/judith) was powered on but its WSL was cold/unresponsive — the `wsl.exe ... tmux list-sessions` command connected, then hung. Symptom looked like "stuck waiting to attach" even though it never got past the listing stage.

Fix pattern: wrap probe SSH in `timeout` — `timeout -k 1 N ssh ...` bounds the whole command no matter where it stalls. Apply to listing/probe SSH only, never the interactive `ssh -t` attach/create path. See `mux.org`'s `ssh_probe` helper (T480s, 2026-06-25).

## `ethtool -t <iface> offline` is destructive — never run it as a diagnostic

`ethtool -t` is a hardware self-test, not a query. It resets the adapter, and on an e1000e whose TX ring is already hung it NULL-derefs in `e1000_flush_desc_rings()`; the `ethtool` process then exits with IRQs disabled, wedging userspace and forcing a power cycle. Read-only ethtool verbs: `-S` (stats), `-a` (pause), `-k` (offloads), `-i` (driver), `-g` (rings), `--show-eee`, and bare `ethtool <iface>`. Everything else — `-t`, `-A`, `-K`, `-G`, `-r`, `--set-eee` — mutates adapter state. Ask before running any of them (T480s, 2026-07-09).

## Link up at full speed but zero packets sent: read the pause-frame counters first

Carrier at 1000/full, `tx_errors=0`, `rx_crc_errors=0`, no PCIe AER, yet `tx_packets` never increments — check `ethtool -S <iface> | grep flow_control` before blaming the NIC, the driver, or the kernel. A link partner jamming PAUSE stops the MAC transmitting exactly this way: thousands of `rx_flow_control_xoff` against almost no `xon`, ~30/s (the 33.5ms max pause quanta at 1 Gbps, refreshed just before expiry). Fix the switch, not the host — power-cycling a wedged unmanaged switch clears it.

The discriminator against a real driver bug is the **absence** of `Detected Hardware Unit Hang`: a genuine e1000e TX-ring stall always prints it with TDH/TDT register dumps, whereas a pause deadlock only trips the generic `NETDEV WATCHDOG: transmit queue 0 timed out`. Ignore the internet's universal `ethtool -K <iface> tso off` advice for I219 — the driver already disables TSO at probe, so it is always already in effect. A pause storm also **masks** any genuine TX hang underneath it; re-check once the link is quiet (T480s + T480, 2026-07-09).

## An I219 MAC can stay wedged across `modprobe -r e1000e`

Reloading the driver does not reset I219 MAC/PHY state — it is shared with the Intel ME. If a freshly loaded e1000e still hangs on the very first packet (`TDH <0>` / `TDT <1>`, one descriptor queued, head never advances) on an idle link, cold-power-off the machine before suspecting dead silicon. A warm reboot may not clear it; a full power-off does (T480s, 2026-07-09).

## `err -30` (EROFS) after a forced shutdown is not evidence of a failing disk

`EXT4-fs (dm-0): ext4_do_writepages: jbd2_start: ... err -30` only means writes hit a read-only filesystem. An operator SysRq remount-read-only (the `U` in REISUB) produces it *byte-identically* to a journal abort. Two discriminators settle it: ext4 records `FS Error count` / `First error time` permanently in the superblock (`dumpe2fs -h <dev>`) on any real filesystem error, and a genuine abort *always* logs `Aborting journal`. If both are absent, no abort occurred. Grep the log for `sysrq: Emergency Remount R/O` before raising a failing-drive alarm, and confirm with `smartctl -H -A`. A `jbd2` token inside a kernel oops backtrace's `Modules linked in:` line is not an error message (T480s, 2026-07-09).

## Neovim "No parser for language X" under heavy load is not a config bug

When load average is very high (rustc/Guix builds + llama-server + stacked agent processes), Neovim 0.12's dlopen-based treesitter parser attach can fail transiently and NON-DETERMINISTICALLY for parsers that are installed and correctly declared — same command succeeds and fails across consecutive runs, hitting bash/python/json/yaml alike while lua/vim/markdown (rtp-bundled) never fail. Before editing lazy.lua's ensure_installed, check `uptime`: if load is in the tens, reopen the file or wait for the build storm to pass. Proven by falsification 2026-07-10 (three config hypotheses tested and reverted; pristine config reproduced the failure identically at load ~29, T480s).

## X230 guix "corrupt input while restoring archive" / "mkdir: File exists" is ZFS unicode normalization, not corruption

The X230's root pool (`rpool/ROOT/ubuntu_n72ogo`, holding `/gnu/store`) has `normalization=formD` + `utf8only=on` — both immutable after dataset creation. Any nar/archive containing filenames that differ only by UTF-8 normalization form CANNOT be restored there: the second name collapses onto the first and mkdir fails with `File exists`, which guix reports as `corrupt input while restoring archive from socket`. It is not a corrupt substitute, not transient, and no server/retry/`--fallback`/`guix gc -D` cycle will ever fix it. Known carrier: `libsass-3.6.4-checkout` (test fixtures `test/e2e/unicode-pwd/Sáss-UŢF8` in NFC and NFD), retained as a runtime reference by guix's `hugo` package output — so hugo (and anything else whose closure contains such an archive) cannot exist in the X230 store at all; `guix copy` from a healthy machine fails identically at unpack. Remedies are topology-level only: per-host manifest exclusion of the affected package, or a store dataset without formD (means recreating the dataset). Burned a full day of substitute-corruption theories 2026-07-10 before `guix copy`'s verbose unpack error named the colliding path.

## Tailnet ACL reachability is tested with `tailscale ping`, never a port probe

`nc -z host 22` conflates "walled by ACL" with "no listener on that port" — a Windows box with no sshd times out identically to a blocked one, and an ACL was nearly misdiagnosed as broken this way (2026-07-11). `tailscale ping -c 5 <host>` tests the WireGuard path itself, independent of services; idle NAT'd peers may need several attempts (`-c 5`) to wake via DERP. Second trap the same day: ACL packet-filter drops happen after decryption, so the tunnel pings fine while a specific src→dst pair is dropped silently — invisible to tcpdump on either end. When one peer reaches a host and another cannot, read the target's inbound filter (`tailscale status --json` or the admin console), don't chase the network.

## A running binary can't be overwritten in place — curl to temp + `mv`

`curl -o ~/.local/bin/tool` onto a binary that is currently executing fails with `curl: (23) Failure writing output` ("text file busy" underneath), so self-hosted daemons silently never update through a naive download lane (herdr on X230 stayed at 0.7.1 this way, 2026-07-11). Download to `dest.tmp.$$`, `chmod +x`, then `mv -f` — rename is atomic and lands even while the old binary runs. The `app-apply` curl_bin lane does this correctly now; keep the pattern for any ad-hoc binary fetch.
