---
name: palmcortex-client
description: Load a client profile and infrastructure context for PalmCortex sessions — comms, billing history, hosting details.
---

*description: Load a client profile and infrastructure context for PalmCortex sessions — comms, billing history, hosting details.*

> **Model:** `gpt-5.4` | **Effort:** `medium` | **Delegate:** `standard`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

## PalmCortex Client Context

Client profiles live at `CORTEX/GoldenAge_Loom/PalmCortex/Clients/{slug}/profile.md`.

Nextcloud legacy assets: `~/mnt/x230/Nextcloud/Clients/{name}/`

### Active Clients

| Slug | Name | Domain | Status |
|------|------|--------|--------|
| Steve-Willis | Steve Willis | lightwizard.com.au | Active — hosted on Vultr |
| Judith-Abeler | Judith Abeler | — | Active |
| Hunter-Pavers | Hunter Pavers | hunterstone.com.au | Active |
| Phonemic-Intelligence | Phonemic Intelligence | — | Active |
| Pillai-Center-Germany | Pillai Center Germany | — | Active |
| ShreemBrzee | ShreemBrzee | — | Active |
| Siddha-Bioscience | Siddha Bioscience | — | Active |
| Anderson-Debernardi | Anderson Debernardi | — | Active |
| Tomasz | Tomasz | — | Active |
| Viviana-Davies | Viviana Davies | — | Active |
| Gillian | Gillian | — | Active — OT/NDIS Obsidian vault |
| Dr-John-Davies | Dr John Davies | — | Active — tech support (Viviana's husband) |
| Duncan-Legal | Marg Duncan | Duncan.Legal | Unknown — stub |
| Alberto-Pires | Alberto Pires | — | Unknown — stub |

### Usage

When asked to handle a client situation:
1. Read the profile: `Clients/{slug}/profile.md`
2. Check `Invoices.md` for billing status
3. Check LOGS for any recent session history: `LOGS/Perplexity/.EXPORT/PalmCortex - LightWizard/` (Steve)
4. Draft comms to match the client's register

