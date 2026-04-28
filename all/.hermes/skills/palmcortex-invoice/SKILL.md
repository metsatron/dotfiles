---
name: palmcortex-invoice
description: Generate a PDF invoice for a PalmCortex client using the palmcortex-invoice pipeline — Markdown data file → Pandoc → Chromium → PDF.
---

*description: Generate a PDF invoice for a PalmCortex client using the palmcortex-invoice pipeline — Markdown data file → Pandoc → Chromium → PDF.*

> **Model:** `gpt-5.4` | **Effort:** `medium` | **Delegate:** `standard`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

## PalmCortex Invoice Pipeline

Generates branded PDF invoices matching the Tiago Pires: Lifestyle Technology style.

**Script:** `FORGE/bin/palmcortex-invoice`
**Template:** `CORTEX/GoldenAge_Loom/PalmCortex/Templates/invoice.html`
**Example data:** `CORTEX/GoldenAge_Loom/PalmCortex/Templates/invoice-example.md`
**Logo source:** `ROOTS/Nextcloud/Clients/Tiago Pires Lifestyle Technology/Logo/`
**Output archive:** `CORTEX/GoldenAge_Loom/PalmCortex/Clients/{slug}/`

### Data file format

Create a `.md` file with YAML frontmatter:

```yaml
---
client: "Client Name"
date: "17 April 2026"
due_date: "24 April 2026"
time_detail: "Flat fee"          # or multiline block with actual/billed hours
amount: "100.00"
subtotal: "100.00"
total: "100.00"
paid: "-"                        # dash if unpaid, amount if partially paid
total_due: "100.00"
---

Description of work performed (markdown — becomes the DESCRIPTION column).

- Line item detail
- Additional items

**Rate:** $75/hour  ← or flat fee
```

### Workflow

1. Copy `invoice-example.md` → `{Client} - Invoice - {Date}.md`
2. Fill in all YAML fields and write the description body
3. Run: `palmcortex-invoice "{Client} - Invoice - {Date}.md"`
4. Review the output HTML, then copy PDF → ROOTS client folder
5. Update `PalmCortex/Invoices.md` with the new entry
6. Send PDF to client

### Business details (hardcoded in template)

- ABN: 87 552 246 212
- GST: not registered — no GST on invoices
- Bank: ANZ — BSB 013 441 — Account 5189 42895 — Ref: Consulting
- Rate: $75/hour (standard) unless agreed otherwise

### Notes

- PDF backend: LibreOffice headless (`libreoffice --headless --convert-to pdf`)
- WeasyPrint is the intended Lane 2 backend — pending encoding into `CORE/anaconda3/`; LibreOffice is the interim path
- Ungoogled Chromium Flatpak was tested but fails with bwrap sandbox mount error (config path issue)
- Invoice naming convention: `{Client} - Invoice - {YYYY-Mon}.pdf`

