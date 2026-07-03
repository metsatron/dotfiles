---
title: "The Armory — Stack"
description: "The tools I actually use, and the doctrine behind them."
---

The doctrine is simple: everything declared, everything reproducible, nothing rented. If a machine dies, I clone one repository and I am home again. If a company dies, I lose nothing, because none of my computing lives in anyone's cloud but mine. Twenty years of DevOps taught me that convenience is how you end up owned — so the entire operating layer is source code, and the source is public.

DotCortex rides on top of any OS as a super system — that is its point. It is not a distribution and does not want to be one; it assumes nothing about what is underneath except a POSIX shell and a package manager it can drive. The distro becomes a substrate detail. The system — the configuration, the packages, the workflows, the aesthetic, the agents — lives one layer up, in source I own, and lands identically on whatever the hardware happens to be running.

## DotCortex

The centre of the armory is **DotCortex**, my literate dotfiles grimoire: Org-mode source that tangles into host-scoped overlays, which a Guile-powered control plane called the Loom weaves onto living machines with GNU Stow. One repo declares the packages (Guix, apt, Flatpak, pip, npm, cargo and more, each as a manifest), the shell, the editor, the desktop styling, the backup rituals, and the machine-specific state for every host I run — without ever making private state public.

Read it yourself: [GitHub](https://github.com/metsatron/dotfiles) / [GitLab](https://gitlab.com/metsatron/dotfiles). This site's source lives in the same repo. That is not a gimmick — it is the point. A stack you cannot read is a stack you have to trust, and I do not extend trust to software.

Reproducibility is worth the most to the least standard user. Someone whose taste fits the defaults does not need any of this — their whole computing life ships preinstalled. Mine does not fit any defaults, which is exactly why it is declared: the bitmap fonts, the retro desktop grammars, the emulation curation, the agent harness — none of it exists in anyone's distro, and all of it rebuilds from one clone. Nobody else's dotfiles could produce my machines. Mine provably do.

## The base

Devuan underneath — Debian without systemd — with GNU Guix on top for reproducible, declarative packages. Emacs is the workshop: the dotfiles are literate Org-mode, so the configuration is a document and the document is the configuration. The fleet is mostly old ThinkPads, deliberately: machines with open documentation, replaceable parts, and Coreboot-compatible firmware — every machine in the fleet can run free boot firmware — on a stack light enough that "obsolete" hardware outperforms most people's new laptops. Even my phone is in the loom, through Termux.

## The server side

For hosting — mine and my clients' — the shape is boring on purpose: Linux VPS, Docker Compose, Nginx reverse proxy, Let's Encrypt, off-site encrypted backups. Two decades of production support across AWS, Odoo, Magento, WordPress and WooCommerce taught me what actually fails at 3 a.m., and the answer is almost always the clever part. So there is no clever part.

## The agents

The newest wing: agentic systems. My AI tooling is configured the same way as everything else — as literate source in DotCortex, tangled and version-controlled, with the agents working inside a knowledge architecture I own rather than a chat window someone else owns. The models are rented, for now. The memory, the harness, and the work are not.

What runs on all this is in [the Cathedral](/work/); the machines themselves live in [the Sanctuaries](/sanctuaries/).
