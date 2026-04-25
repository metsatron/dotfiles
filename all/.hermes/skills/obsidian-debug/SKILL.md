---
name: obsidian-debug
description: Debug live Obsidian runtime behavior through DevTools and CDP, with Flatpak-specific caveats, probe patterns, and performance triage.
---

*description: Debug live Obsidian runtime behavior through DevTools and CDP, with Flatpak-specific caveats, probe patterns, and performance triage.*

> **Model:** `gpt-5.4` | **Effort:** `high` | **Delegate:** `claude-sonnet`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# Obsidian Debug

Use this skill for live Obsidian runtime debugging when `obsidian devtools` or `obsidian dev:cdp` are the main instruments.

Load `obsidian-cli` alongside this skill.

## Flatpak Reality Check

- Standard `obsidian` subcommands may return hollow output under Flatpak even when the app is running.
- `obsidian devtools` may still work.
- `obsidian dev:cdp` can be the reliable path into the renderer when `dev:console`, `dev:errors`, `vault`, or `plugins:enabled` are hollow.
- dbus and GTK warnings on stderr are usually transport noise, not the actual payload.

## Primary Tools

- `obsidian devtools`
- `obsidian dev:cdp method="Runtime.evaluate" params='{"expression":"..."}'`
- `obsidian dev:cdp method="Performance.enable"`
- `obsidian dev:cdp method="Performance.getMetrics"`
- `obsidian dev:cdp method="Memory.getDOMCounters"`
- `obsidian dev:cdp method="HeapProfiler.collectGarbage"`

## High-Value Probes

- plugin state: `Array.from(app.plugins.enabledPlugins)`
- metadata pressure: `app.metadataCache.inProgressTaskCount`
- workspace leaves and visible node counts
- Chrome counters: DOM nodes, event listeners, JS heap
- retained-state diagnosis: compare visible DOM against `Memory.getDOMCounters`

## Debug Heuristics

- Huge heap plus huge node/listener counts with a small visible DOM points to retained detached state, not merely a large open note.
- If the issue persists with heavy dynamic plugins disabled, inspect the baseline QoL plugins and saved workspace state.
- Stale leaves from disabled plugins are worth treating as suspects even when their current visible node count is small.
- Prefer a full manual quit and relaunch over `obsidian restart` when establishing a clean baseline.

## Runtime Probe Pattern

When you need time-series evidence rather than one-shot numbers, inject a temporary `window.__helmProbe` sampler that records:

- event-loop lag
- metadata progress
- work-queue activity
- nav-file and nav-folder counts
- active leaf type and title
- warnings and errors intercepted from `console.warn` / `console.error`

Read the probe back through `Runtime.evaluate` and persist the results into MetaCortex before the session is closed.

## Rules

- never call a restart-generated state a clean baseline without re-measuring after a full quit
- force-GC results matter: if `HeapProfiler.collectGarbage` does not reduce counters, the leak is strongly retained
- preserve exact metric values in notes; do not round away the order of magnitude

## Canonical Note Target

- `CORTEX/GoldenAge_Loom/MetaCortex/Debugging/obsidian-flatpak-cdp-debugging.md`

