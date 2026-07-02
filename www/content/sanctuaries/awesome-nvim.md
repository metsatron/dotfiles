---
title: "KiTTY OS — The Neovim Sanctuary"
description: "How close to Emacs can a GPU-accelerated terminal get? The terminal as operating system, CLI-native and LLM-native."
skin: nvim
weight: 4
---

On paper this is the Lua mirror of [the Emacs sanctuary](/sanctuaries/emacs/): AwesomeWM ruling the windows, Neovim as the IDE surface. But the real goal is a question: **how close to Emacs can we get KiTTY?**

Kitty is a GPU-accelerated terminal with a graphics protocol, and that changes what "terminal" means. The target is a terminal that behaves like an operating system: Org-mode and Markdown rendered at variable font heights inside Neovim; web browsers running in terminal panes against local servers; LLMs not just writing prose into buffers but generating HTML and JavaScript that renders directly in a terminal browser pane; local and remote databases on tap; the Obsidian CLI treated as a queryable database rather than a note-taking app; Org-roam rendered in the terminal, where the graph actually lives.

Emacs stays in the picture — as a compiler. And the far horizon is the absorbing move: full variable-height terminal Emacs, so that Kitty absorbs Emacs and the last GUI dependency dissolves. At that point everything is CLI-native and LLM-native — one text-shaped surface that humans and models read and write the same way, with the GPU making it beautiful. The terminal stops being a window onto the system and becomes the system.

The law that keeps it honest is the same as everywhere in the habitat: Guix owns the binaries — Neovim, Kitty, every language server — and DotCortex tangles the configuration. No Mason pulling binaries from the network, no config islands outside the tangle. Screenshots when it breathes.
