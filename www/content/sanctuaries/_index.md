---
title: "The Castle — Sanctuaries"
description: "Inhabited desktops: real operating systems, kept alive and lived in."
---

I keep a fleet of operating systems alive — not as museum pieces but as inhabited spaces. Each one has its own desktop grammar, its own mood, its own journal, and its own resident AI agent. The project is called the **Virtual Habitat**, and it runs on a simple architecture: DotCortex tangles each guest's configuration from literate Org source into host-visible home directories, which are projected into the guest. The disk image holds the OS; everything worth editing, inspecting, and preserving lives in ordinary files on the host. No cracking open disk images to fix an Emacs config.

The vocabulary is precise. A **sanctuary** is a long-lived, curated container — shared kernel, own environment, own identity. An **enclave** is a full virtual machine with its own kernel. An **archipelago** is an enclave with satellite systems nested inside it. And beyond those, the emulation tier: foreign CPU architectures brought back breathing. Sanctuaries share one Guix store underneath, so habitats grow as configurations, not as duplicated systems — adding a new one costs a declaration, not a disk image.

Each sanctuary below has its own page, and each page wears the skin of the system it shelters. That is not a gimmick either — spatial memory is real, and a space you can recognise at a glance is a space you can live in.

## The wider fleet

Behind the active sanctuaries stands the enclave fleet, and it splits cleanly in two (ruling dated 2026-07-02).

The **living tier** comes first: operating systems with a real future, kept as priority enclaves rather than exhibits — GhostBSD and its Gershwin desktop, Haiku (the continuation of the BeOS grammar this whole site borrows), and KolibriOS, an entire graphical OS written in assembly that boots before your finger leaves the key. Alongside them, OpenBSD and OpenIndiana. These get lived in, updated, and argued with.

Everything else is honest archaeology, and proud of it: Solaris 10 under CDE, Solaris 2.6 under OpenWindows, NeXTSTEP 3.3 and OPENSTEP 4.2, BeOS R5 itself. Then the deep emulation tier, where the CPU itself is software: IRIX 6.5 on emulated SGI hardware, HP-UX on PA-RISC, Tru64 on Alpha. Old operating systems are not dead software. They are alternative answers to questions the industry stopped asking.
