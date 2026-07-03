---
title: "The Emacs Sanctuary"
description: "Guix + Qtile + a topology of independent Emacs processes."
skin: emacs
weight: 3
---

The working sanctuary: a Guix-backed container built around a topology of independent Emacs processes. Three boot profiles share one body — Qtile ruling the windows today, StumpWM as the Lisp-native second opinion, and probably EXWM in the end — the same sanctuary wearing three window managers, because declarations make profiles cheap. Inside a nested display the window manager is not the host's problem, so Emacs may as well own the whole X session. The topology: one for core work, one as a disposable launcher frame, one for dashboards, one for agent sessions and long-running tools, one for journals. Each has its own socket, state, and entrypoint. One shared constitution, multiple independent bodies: a wedged agent Emacs cannot freeze the launcher.

The launcher pattern is the part I am fondest of: a single chord summons a minibuffer-only floating Emacs frame that resolves applications, project commands, and portals into the other sanctuaries, then destroys itself. No menu bar, no dock, no start button — a question asked and answered.

Once the pattern is fully proven, this sanctuary is promoted: reborn as a full Guix System virtual machine — own kernel, Shepherd init, a real GNU operating system generated from declaration rather than installed by hand. Screenshots when it breathes.
