---
title: "It Rides on Top"
description: "DotCortex is not a distribution and does not want to be one. On super systems, the platform-swallowing law, and why reproducibility is worth the most to the least standard user."
date: 2026-07-04
draft: true
weight: 10
---

Every time a screenshot of one of my machines makes the rounds, the first question is the same: *what distro is that?*

It is the wrong question, and the wrongness is the whole point.

The distro under any of my machines is boring on purpose. A stable Debian-family base here, a Guix profile layer there — pick one, it barely matters. Everything you are actually looking at — the desktop that reads like a lost SGI workstation, the BeOS grammar, the terminal that behaves identically on a ThinkPad from 2012 and a phone from 2024 — none of that lives in the distribution. It lives in a single version-controlled repository that rides on top of whatever operating system happens to be underneath. I call the layer a **super system**. It assumes nothing about its host except a POSIX shell and a package manager it can drive.

## The platform-swallowing law

There is an old law in computing that platforms are swallowed by what rides on them. DOS mattered until Windows rode on it; then nobody chose a machine for DOS. Windows mattered until the browser rode on it; then the operating system became a bootloader for Chrome. The value always migrates up the stack, to the layer where a person actually lives.

Distributions know this, which is why they fight so hard to be identities instead of substrates. The tribal energy around distro choice — the flame wars, the conversion stories, the them-and-us — is a platform layer trying desperately not to be swallowed.

I opted out of the fight by accepting the law instead. Let the base be a substrate. Let it be replaceable, boring, dignified in the way plumbing is dignified. The layer I own — the layer that carries twenty years of my working life — sits above every distribution and survives all of them. When a base OS disappoints me, politically or technically, I change tenants. The estate stays.

## What the layer is

Mechanically, it is dotfiles the way a cathedral is stones.

The whole system is written as literate Org documents — prose and configuration interleaved, the reasoning next to the code it justifies. Those documents tangle into real config files, which are overlaid onto the machine with GNU Stow. Package manifests — Guix, apt, pip, npm, Flatpak, cargo and the rest — are declared in the same sources and applied by the same tooling, so a machine's installed software is as version-controlled as its keybindings. One control plane drives it: a small verb grammar that tangles, stows, applies manifests, and syncs a fleet — currently three ThinkPads and a phone — from a single repository.

The result is that a machine, to me, is a cache. The truth is the repo.

## Reproducibility is worth the most to the least standard user

Here is the argument nobody makes, and it is the one that matters.

The standard advice says reproducibility is for fleets, for enterprises, for people with compliance departments. A regular user with a regular setup can just reinstall — the reasoning goes — so declarative systems are over-engineering for the desktop.

That reasoning is exactly backwards, because it prices reinstallation at the cost of the *standard* setup. A standard setup is cheap to lose: it is an hour of clicking through installers, and everything you had is on someone's app store. The further you drift from standard, the more catastrophic loss becomes — and the drift is where all the value lives. A desktop tuned across two decades. Fonts patched by hand. Emulation sanctuaries with their own themed rooms. A window manager configuration that encodes muscle memory older than some of my clients. None of that can be re-derived from memory, and no installer on earth ships it.

The least standard user has the most to lose, and is therefore the person reproducibility was actually invented for. Enterprises can afford to lose a workstation. I cannot afford to lose mine — so I made mine impossible to lose.

## The receipts

This is a practiced position, not a posted one, so the claims come with receipts.

Every machine I operate is produced from the one public repository — the same literate sources, the same manifests, the same overlay tooling, differing only in a per-machine layer as thin as the machines' differences really are. A fresh ThinkPad becomes one of my machines in an afternoon, unattended for most of it. The desktops that have made the front page of r/unixporn were not screenshots of a lucky arrangement; they were checkouts. When the repository's history needed rewriting this month, I rewrote it, re-synced the fleet against the new history, and every machine agreed about reality again by lunch — because agreement about reality is what the layer *is*.

Nobody else's dotfiles could produce my machines. Mine provably do.

## The quiet part

There is a sovereignty argument under all of this, and I will make it plainly and briefly.

Whoever owns the layer you live in, governs you. If your working life lives in a distribution's defaults, a desktop environment's decisions, a vendor's cloud — then their politics, their captures, their reversals are yours to absorb, and you will absorb them on their schedule. I have watched that machinery up close, and I have written elsewhere in this room about what governs my own repositories instead.

A super system is the practical shape of the refusal. It does not ask the base to be virtuous. It asks the base to be *replaceable* — and keeps everything that matters where no one can vote on it but me.

The stop light gets stolen by whatever rides on top. Ride on top.
