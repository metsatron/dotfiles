---
title: "It Rides on Top"
description: "DotCortex is not a distribution and does not want to be one. On super systems, the platform-swallowing law, and why reproducibility is worth the most to the least standard user."
date: 2026-07-04
draft: false
weight: 10
---

My digital life has died more than once. Moving back to Australia from Berlin, a bag of SSDs corrupted in transit. Another time, index corruption in my ZFS pool put thirty-two gigabytes of the only data that can never be re-derived in mortal danger: recordings of almost every ceremony I have run or sat in, icaros sung by my maestros, mantras from my Guru, the first websites I built in high school, videos of me as a baby in Portugal and the Canary Islands. I lost the firmware maps of my custom keyboard and not much else, and I pulled the rest back off dead drives — more than once, with no backups and no right to succeed. Everything about how my machines are built now follows from those nights.

So when a screenshot of one of my desktops makes the rounds and the first question is *what distro is that?* — it is the wrong question.

The distro under any of my machines is boring on purpose. A stable Debian-family base here, a Guix profile layer there — pick one, it barely matters. Everything you are actually looking at — the desktop that reads like a lost SGI workstation, the BeOS grammar, the terminal that behaves identically on a ThinkPad from 2012 and a phone from 2024 — none of that lives in the distribution. It lives in a single version-controlled repository that rides on top of whatever operating system happens to be underneath. I call the layer a **super system**, and the name is not a coinage for this essay: the repository turns a decade old this year, and the name assembled itself in bits and pieces across most of that decade before settling, this last year, as RMS-GSS — *Generative Super System*. The repo has outlived every substrate that tried to be permanent underneath it. It assumes nothing about its host except a POSIX shell and a package manager it can drive.

## The platform-swallowing law

There is an old law in computing that platforms are swallowed by what rides on them. DOS mattered until Windows rode on it; then nobody chose a machine for DOS. Windows mattered until the browser rode on it; then the operating system became a bootloader for Chrome. The value always migrates up the stack, to the layer where a person actually lives.

Distributions know this, which is why they fight so hard to be identities instead of substrates. The tribal energy around distro choice — the flame wars, the conversion stories, the them-and-us — is a platform layer trying desperately not to be swallowed.

I opted out of the fight by accepting the law instead. Let the base be a substrate. Let it be replaceable, boring, dignified in the way plumbing is dignified. The layer I own — the layer that carries twenty years of my working life — sits above every distribution and survives all of them. When a base disappoints me — and lately the disappointments are political far more often than technical — I change tenants. The estate stays.

## What the layer is

Mechanically, it is dotfiles. But I told a friend once what it actually is, and I stand by the words: it is not a cathedral. It is my Maloca — the ceremony temple in the middle of the jungle, roots and leaves everywhere, organic and recursive, closer in spirit to Terry Davis's TempleOS than to any distribution: a sovereign space where a man communes with the Divine through his own machine, with zero fucks given about what anyone thinks of his madness.

The whole system is written as literate Org documents — prose and configuration interleaved, the reasoning next to the code it justifies. Those documents tangle into real config files, which are overlaid onto the machine with GNU Stow. Package manifests — Guix, apt, pip, npm, Flatpak, cargo and the rest — are declared in the same sources and applied by the same tooling, so a machine's installed software is as version-controlled as its keybindings. One control plane drives it: a small verb grammar that tangles, stows, applies manifests, and syncs a fleet — currently three ThinkPads and a phone — from a single repository.

The result is that a machine, to me, is a cache. The truth is the repo.

## Reproducibility is worth the most to the least standard user

Here is the argument nobody makes, and it is the one that matters.

The standard advice says reproducibility is for fleets, for enterprises, for people with compliance departments. A regular user with a regular setup can just reinstall — the reasoning goes — so declarative systems are over-engineering for the desktop.

That reasoning is exactly backwards, because it prices reinstallation at the cost of the *standard* setup. A standard setup is cheap to lose: it is an hour of clicking through installers, and everything you had is on someone's app store. The further you drift from standard, the more catastrophic loss becomes — and the drift is where all the value lives. A desktop tuned across two decades. Fonts patched by hand. Emulation sanctuaries with their own themed rooms. A window manager configuration that encodes muscle memory older than some of my clients. None of that can be re-derived from memory, and no installer on earth ships it.

The least standard user has the most to lose, and is therefore the person reproducibility was actually invented for. Enterprises can afford to lose a workstation. I cannot afford to lose mine — so I made mine impossible to lose.

The friend who understood this first is a Guix developer. His projects ship a code of conduct; I wrote a Code of Sovereignty in explicit refusal of them — and the thesis of this essay was spoken between us in both directions anyway. When my drives died he put it plainly: with a declarative system, reinstalling and getting back to the same state is a matter of hours, not days — and it comes back one hundred percent how you want it, not in an *oh, I forgot that package and that setting* state. Backups are for user data; the system itself should be a build artifact. Then he offered his hands for the migration before I asked. The capture I describe below works by hijacking real empathy and weaponizing it into boards and purges. His is the un-hijacked kind, aimed person to person. The ideological axis decides which lineages I will build on; it does not decide whom I weave with. He and I were weaving on a layer above it, where spiritual alignment is the load-bearing pillar and the political one recedes. The war is against the capture. It was never against him.

## The receipts

This is a practiced position, not a posted one, so the claims come with receipts.

Every machine I operate is produced from the one public repository — the same literate sources, the same manifests, the same overlay tooling, differing only in a per-machine layer as thin as the machines' differences really are. A fresh ThinkPad becomes one of my machines in an afternoon, unattended for most of it. The desktops that have made the front page of r/unixporn were not screenshots of a lucky arrangement; they were checkouts. When the repository's history needed rewriting this month, I rewrote it, re-synced the fleet against the new history, and every machine agreed about reality again by lunch — because agreement about reality is what the layer *is*.

## The quiet part

There is a sovereignty argument under all of this, and it is not an afterthought. It is the founding reason the layer exists — I wrote it into the repository itself, under the Code of Sovereignty. This essay is the architecture that makes it enforceable.

What is happening to free software is not drift. It is capture, and the method is the oldest game of epistemic warfare on record: capture the syntax and you capture the thought. The Soviets ran it as active measures — linguistic programming, syntax substitution, symbolic inversion: take a people's words, hollow them, hand them back inverted, and wait for the minds to follow the language. Jordan Peterson was the canary in the coal mine, and the warning was precise: compelled speech is worse than censorship, because what you cannot say, you soon cannot think. Their terms are themselves the payload — adopt the vocabulary and you have already adopted the verdict.

And do not file this under anyone's partisan grievance — the partisan frame is itself part of the payload. The circles I felt most at home in for most of my life were the ones the operation captured first, and I watched that home turn terminal-stage pathological under sustained psyops. Nor was any cohort spared: fifth-generation warfare does not run one script, it runs a tailored script per audience, and every tribe got the payload built for its own reflexes. Contrast is a gift; capture is the theft of it.

Now run the checklist against the ecosystem. Codes of conduct imported wholesale as political instruments and enforced as Maoist purity purges. Project governance replaced by Soviet-style moderation boards holding veto power above the maintainers and the founders themselves. Builders ejected from projects they created, in language borrowed from struggle sessions, while the foundations answer to their corporate sponsors and call it community. The language mandates enforced through GitHub as the compliance layer. Rustify everything. And it does not stop at the operating system: the same capture runs through the Rust and Python foundations into Unity and Unreal — the engines that will render the coming augmented-reality layer, the software that will sit between human eyes and the world. These technologies are colonizing minds, and whoever owns the syntax of the layer you live in owns what can be said in it, and then what can be thought in it.

I use the old word for this because the old word is the accurate one: it is communism — an operating system, and it ports. It has run on empires, on universities, on foundations; now it is being ported onto the substrate that renders reality itself, and the roadmap runs from captured engines to captured language to proteins folded into a compliant shape. The playbook has already been executed once at full scale on life itself: the man who captured and strip-mined the personal computer's operating system went on to run the same colonization on seeds, soil, and the microbiome. Dr. Vandana Shiva has spent decades documenting that conquest and naming its author; I only add the older spelling of what he is — Ba'al Gates. Followed to its end, this trajectory is orders of magnitude darker than 1984, darker than Brave New World — an evil of a scale the twentieth century's designated monsters could not have conceived, however useful their silhouettes remain as the approved boundary of imaginable evil.

The lineage of a distribution — who governs it, who funds it, whom it ejects and how it speaks while ejecting them — is therefore not noise around a technical artifact. It is part of the artifact's fitness, and by that criterion whole houses I once respected are no longer fit to be trusted with my working life. Because whoever owns the layer you live in, governs you. If your working life lives in a distribution's defaults, a desktop environment's decisions, a vendor's cloud — then their politics, their captures, their reversals are yours to absorb, on their schedule, forever. The only escape that doesn't cost you your life's work is to make the governed layer thin and the owned layer total.

This is the oldest problem there is, and the durable answer was found long ago by people with far more to lose than dotfiles. Portugal, where I am from, converted its Jews at sword-point in 1497. The families that survived as themselves — some for three centuries, under an Inquisition purpose-built to find them — did it by moving everything sacred into the smallest portable form: the law carried in memory, the rite folded into the kitchen, the calendar hidden inside the visible one. House, land, even the name were surrendered as substrate — replaceable, and replaced. What made them who they were rode on top, invisible to the authority that owned the ground. The estate was never the land. The estate was the scroll.

A super system is that shape, in git. It does not ask the base to be virtuous — no base will be, and the ones that advertise virtue loudest are the ones furthest into capture. It asks the base to be *replaceable*, and keeps everything that matters — the law, the memory, the twenty years — where no one can vote on it but me.

Ride on top.
