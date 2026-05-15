# Customer — PowerPlay Brands

PowerPlay is the **first customer** on the New Business Agent platform. Pilot scope: build a qualified new-business pipeline of EU and UK retailers for PowerPlay's licensed-apparel programmes.

## Pilot deliverable shape

- **Spreadsheet-only.** The customer-facing artefacts are XLSX and CSV files — there is no Airtable, no Salesforce, no SaaS dashboard. (Airtable remains available in the codebase as a future feature add-on; see `ops/airtable_schema.md`.)
- **Persistence substrate:** SQLite, single `.db` file in the container volume at `data/powerplay/pipeline.db`. Trivially backed up; trivially inspected with any SQLite client.
- **Customer reviews via:** the weekly XLSX snapshot workbook (`pipeline_powerplay_<date>.xlsx`) attached to the digest email, plus an editable `approvals_inbox.csv` for HITL decisions during calibration.

## Deployment summary

- **Vertical pack:** `brand_licensing_b2b`
- **Hosting:** dedicated Docker container on Agentic Engineering's shared Hostinger UK VPS, running Paperclip (paperclip.ing) as the control plane.
- **Calibration window:** 6 weeks. During this window, `contact_enricher` writes go through the Approvals queue. The customer reviews `approvals_inbox.csv` and marks decisions in the `decision` column; the Hand-off agent applies them on its next wake. Once approval rate stabilises (>90% sustained for 2 consecutive weeks), the stakeholder approval gate relaxes in `crm.yaml`.

## Files

| File | Purpose |
| :--- | :--- |
| `company.yaml` | Identity + vertical pin |
| `targets.yaml` | What "a good target" looks like for PowerPlay |
| `brand.yaml` | PowerPlay brand voice, signature, visual marks |
| `personas.yaml` | The role-band subset PowerPlay cares about |
| `thresholds.yaml` | Confidence, freshness, scoring overrides |
| `crm.yaml` | SQLite substrate configuration |
| `enrichment.yaml` | Multi-provider enrichment waterfall (Cognism + Apollo + Hunter; Lusha declared but off) |
| `outputs.yaml` | XLSX/CSV snapshot cadence, digest recipients, approvals inbox |
| `agents.yaml` | Which agents are enabled for PowerPlay |

## What does not live here

- The retailer schema, signal taxonomy, fit-score weights, role taxonomy — all of those live in `verticals/brand_licensing_b2b/` and apply to every customer pinned to that vertical.
- Agent SKILL.md files — those live in `nba_platform/agents/`.
- Secrets — OpenRouter API key, Cognism credentials. Those live in Paperclip's secrets store and are referenced by name only in the config files here.

## First-run prerequisites

Before the first agent wakes for PowerPlay, the following must exist:

1. The data directory mounted into the container at the path in `crm.yaml` (`data/powerplay/`). The SQLite file is created automatically on first wake.
2. The output directory mounted at the path in `outputs.yaml` (`data/powerplay/outputs/`).
3. Paperclip secrets configured: `OPENROUTER_API_KEY`, plus per-provider enrichment keys for whichever providers in `enrichment.yaml` are `enabled: true` (`COGNISM_API_KEY`, `APOLLO_API_KEY`, `HUNTER_API_KEY`), `TAVILY_API_KEY`, `COMPANIES_HOUSE_API_KEY`. Providers without credentials are skipped by the router; the deployment doesn't crash, but coverage degrades — get the keys in before the calibration window opens.
4. Paperclip company definition imported from `ops/paperclip_company_template.yaml` and adjusted to point at PowerPlay's customer directory.
5. Email-recipient placeholders in `outputs.yaml` replaced with real addresses.
