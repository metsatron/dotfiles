---
name: virtual-habitat
description: Orient to the Virtual Habitat project — VM/container habitat extending DotCortex. Room registry, current phase, project note locations, guest schema.
model: claude-haiku-4-5-20251001
---

# Virtual Habitat

Use this skill when working on the Virtual Habitat project — the declared VM/container habitat extending DotCortex into a curated fleet of virtual operating systems.

## Project Location

Notes: `~/HelmCortex/CORTEX/GoldenAge_Loom/MetaCortex/Projects/Virtual-Habitat/`
DotCortex org sources: `~/DotCortex/` — **not yet created** (Phase 0 work)
Guest homes: `$XDG_DATA_HOME/dotcortex/guests/<guest-id>/home/` (host-visible, DotCortex tangles here)

## Current Phase

**Phase 0 (DotCortex scope + Guix refactor) → Phase 1A (first Distrobox rooms)**

Nothing in DotCortex yet. Project plan exists in MetaCortex only.

## Sub-notes

- `index.md` — vision, build sequence, Nexus map
- `DotCortex-Scope.md` — org structure, guest schema, loom verbs, transport policy
- `Guix-Package-Commons.md` — profile composability, shared store bind mounts
- `Distrobox-Desktop-Rooms.md` — the three Phase 1 Distrobox rooms
- `Azure-Neptune.md` — Azure Neptune Enterprise Server KVM VM
- `Historical-Unix-Fleet.md` — full OS fleet: tiers, backends, build order
- `Display-Profiles.md` — period-correct CRT/display profiles
- `Sandcastle.md` — ephemeral agent task execution integration

## Room Registry

| Room | Type | Stack | Phase |
|---|---|---|---|
| room-qtile | Distrobox | Guix + Qtile + multi-Emacs | 1A |
| room-gnustep | Distrobox | Window Maker + GNUstep | 1A |
| room-cde | Distrobox | Open CDE from source | 1B |
| azure-neptune | KVM VM | Azure Linux native base + desktop overlay under validation | KVM / parallel |
| openbsd | KVM VM | OpenBSD | 3 |
| openindiana | KVM VM | illumos / OpenIndiana | 3 |
| solaris-10-cde | KVM VM | Solaris 10 x86 | 3 |
| haiku | KVM VM | Haiku R1/beta5 | 3 |
| solaris-2.6 | KVM VM | Solaris 2.6 / OpenWindows | 4 |
| nextstep-3.3 | QEMU | NeXTSTEP 3.3 | 4 |
| openstep-4.2 | QEMU | OPENSTEP 4.2 | 4 |
| irix-6.5.22 | MAME/SGI | IRIX 6.5.22 | 5 |
| hpux-11.11 | QEMU PA-RISC | HP-UX 11.11 | 5 |
| tru64 | QEMU Alpha | Tru64 / DECwindows | 5 |
| beos-r5 | QEMU | BeOS R5 | 5 |
| kolibrios | QEMU | KolibriOS 0.7.7.0 | 5 |

## Guest Declaration Schema (for guests.org once created)

```org
:guest_id:
:arch:                    # x86_64 | mips | parisc | alpha
:acceleration:            # kvm | tcg | mame
:transport:               # virtiofs | nfs | sftp | serial
:ssh_status:              # native | package-needed | serial-only | unsupported
:residency_tier:          # full | relay | museum
:display_profile:         # see display-profiles.org
:guest_home_policy:       # room-rw+cortex-ro | nfs-export | none
```

## Adding a New Room or Guest

1. Add guest declaration block in `all/.config/virtualisation/guests.org` (once that file exists)
2. Add room home directory under `$XDG_DATA_HOME/dotcortex/guests/<id>/`
3. Add Nexus sanctuary folder entry in `NEXUS/sanctuaries/<id>/`
4. Update the `Historical-Unix-Fleet.md` or `Distrobox-Desktop-Rooms.md` sub-note
5. Update room registry table in this skill (via `skills.org` in DotCortex)
