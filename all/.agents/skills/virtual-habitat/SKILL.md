---
name: virtual-habitat
description: Orient to the Virtual Habitat project — VM/container habitat extending DotCortex. Guest registry (sanctuaries/enclaves/emulation), vocabulary, current phase, project note locations, guest schema.
model: claude-haiku-4-5-20251001
---

# Virtual Habitat

Use this skill when working on the Virtual Habitat project — the declared VM/container habitat extending DotCortex into a curated fleet of virtual operating systems.

## Project Location

Notes: `~/HelmCortex/CORTEX/GoldenAge_Loom/MetaCortex/Projects/Virtual-Habitat/`
DotCortex org sources: `~/DotCortex/guests.org`, `distrobox.org`, `qemu.org` (Phase 0A complete ✅)
Guest homes: `$XDG_DATA_HOME/dotcortex/guests/<guest-id>/home/` (host-visible, DotCortex tangles here)

## Current Phase

**Phase 0B (Guix profile refactor) → Phase 1A (first Distrobox sanctuaries)**

Phase 0A complete: `guests.org`, `distrobox.org`, `qemu.org` stubs tangled and stowed.

## Vocabulary

| Term | Meaning |
|---|---|
| **Sanctuary** | Distrobox container — shared host kernel, agent enters via `distrobox exec` (host-mediated relay) |
| **Enclave** | KVM VM — own kernel, hardware-accelerated CPU, agent enters via SSH |
| **Archipelago** | A KVM enclave containing satellite VMs/emulators nested within it |
| **Emulation tier** | QEMU TCG or MAME — software CPU emulation, non-native architecture |
| **Agent pathway validated** | SSH or equivalent doorway confirmed working; residency tier is provisional until true |

## Sub-notes

- `index.md` — vision, vocabulary, build sequence, Nexus map
- `DotCortex-Scope.md` — org structure, guest schema, loom verbs, transport policy
- `Guix-Package-Commons.md` — profile composability, shared store bind mounts
- `Distrobox-Sanctuaries.md` — the three Phase 1 Distrobox sanctuaries
- `Azure-Neptune.md` — Azure Neptune Archipelago (KVM enclave + satellite layer)
- `Historical-Unix-Fleet.md` — full OS fleet: tiers, backends, build order
- `Display-Profiles.md` — period-correct CRT/display profiles
- `Sandcastle.md` — ephemeral agent task execution integration

## Guest Registry

| Guest | Habitat | Type | Stack | Phase |
|---|---|---|---|---|
| sanctuary-qtile | Sanctuary | Distrobox | Guix + Qtile + multi-Emacs | 1A |
| sanctuary-gnustep | Sanctuary | Distrobox | Window Maker + GNUstep | 1A |
| sanctuary-cde | Sanctuary | Distrobox | Open CDE from source | 1B |
| azure-neptune | Enclave | KVM | Azure Linux 4 + archipelago satellite layer | KVM / parallel |
| openbsd | Enclave | KVM | OpenBSD | 3 |
| openindiana | Enclave | KVM | illumos / OpenIndiana | 3 |
| solaris-10-cde | Enclave | KVM | Solaris 10 x86 | 3 |
| haiku | Enclave | KVM | Haiku R1/beta5 | 3 |
| solaris-2.6 | Enclave | KVM | Solaris 2.6 / OpenWindows | 4 |
| nextstep-3.3 | Enclave | KVM x86 | NeXTSTEP 3.3 (x86 port) | 4 |
| openstep-4.2 | Enclave | KVM x86 | OPENSTEP 4.2 (x86) | 4 |
| irix-6.5.22 | Emulation | MAME/SGI | IRIX 6.5.22 | 5 |
| hpux-11.11 | Emulation | QEMU PA-RISC | HP-UX 11.11 | 5 |
| tru64 | Emulation | QEMU Alpha | Tru64 / DECwindows | 5 |
| beos-r5 | Enclave | KVM x86 | BeOS R5 (x86, legacy peripherals) | 5 |
| kolibrios | Enclave | KVM x86 | KolibriOS 0.7.7.0 | 5 |

Residency tier is provisional until `:agent_pathway_validated: true`.

## Guest Declaration Schema

```org
:guest_id:
:habitat_type:            # sanctuary | enclave | emulation
:arch:                    # x86_64 | mips | parisc | alpha
:acceleration:            # kvm | tcg | mame
:transport:               # virtiofs | bind-mount | nfs | sftp | serial
:ssh_status:              # native | package-needed | serial-only | unsupported
:agent_pathway_validated: # true | false
:residency_tier:          # full | relay | museum
:display_profile:         # see display-profiles.org
:guest_home_policy:       # sanctuary-rw+cortex-ro | nfs-export | none
```

## Adding a New Sanctuary or Guest

1. Add guest declaration block in `linux/.config/virtualisation/guests.conf` (via `guests.org`)
2. Add home dirs: `vm-homes-init` (or manually under `$XDG_DATA_HOME/dotcortex/guests/<id>/`)
3. Add Nexus folder entry in `NEXUS/sanctuaries/<id>/`
4. Update the `Historical-Unix-Fleet.md` or `Distrobox-Sanctuaries.md` sub-note
5. Update guest registry table in this skill (via `skills.org` in DotCortex)
