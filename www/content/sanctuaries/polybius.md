---
title: "The Polybius Sanctuary"
description: "An isolated terminal arcade and experiment environment — retro CRT terminal, Bubblewrap containment, persistent dossiers."
skin: polybius
weight: 10
---

The Polybius terminal arcade sanctuary (sanctioned 2026-11-21). A persistent Unix/BBS terminal environment administering authentic CLI games, interactive questionnaires, and profiling exercises under Linux user namespace and resource containment.

## Architecture

Underneath, the standard habitat law applies:
- **Sandbox containment**: Bubblewrap (`bwrap`) isolation with unshared user/PID/IPC/UTS namespaces, read-only system roots, ephemeral tmpfs, and transient cgroup v2 resource limits.
- **PTY Broker**: Master/slave pseudo-terminal lifecycle controller supporting process suspension (`SIGSTOP`/`SIGCONT`), clean window resizing (`SIGWINCH`), and transparent session interruption.
- **Event Journal**: Monotonic, tamper-evident SQLite append-only event stream recording input digests, process states, and behavioral events.
- **Player Dossier**: Deterministic psychological profiling engine projecting gameplay metrics, questionnaire responses, and cross-session audit records.
- **BBS Integration**: Integrated into the Caddy BBS dial-up directory and boards (`/bbs/` and `/dotbbs/`), styled with authentic CP437 VGA typography, 16-colour ANSI palettes, and CRT scanlines.
