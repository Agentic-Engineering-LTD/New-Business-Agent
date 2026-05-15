# Architecture

The platform is organised in three strict layers. The rest of this document explains what lives where, why, and the discipline that keeps the layers from contaminating each other.

```
┌─────────────────────────────────────────────────────────┐
│ customers/<customer>/                                   │
│   identity, branding, target definition, persona subset │
│   thresholds, CRM config, agent toggles, output cadence │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼  loaded by config_loader
┌─────────────────────────────────────────────────────────┐
│ verticals/<vertical>/                                   │
│   record schemas, signal taxonomy, data sources,        │
│   ranking weights, compliance notes, output templates   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼  consumed by agent skills
┌─────────────────────────────────────────────────────────┐
│ nba_platform/                                           │
│   agents (SKILL.md), integrations (adapters),           │
│   governance, evals, outputs, lib                       │
└─────────────────────────────────────────────────────────┘
```

## The three layers

### Platform (`nba_platform/`)

Code and SKILL.md files that are **vertical-agnostic and customer-agnostic**. The QA script enforces this with a leak check: no vertical-specific term may appear in any file under `nba_platform/`. The platform owns:

- **Agents** (`nba_platform/agents/<agent>/SKILL.md`). One SKILL.md per agent role. The skill defines the role boundaries, inputs, outputs, cadence, model role, quality bar, and audit emissions — all in the abstract. Paperclip injects the skill into a heartbeat at runtime; the heartbeat itself can be Claude Code, a Python script with a webhook, or an MCP runtime. The platform does not care.
- **Integrations** (`nba_platform/integrations/<area>/`). Each integration area has a `base.py` defining the abstract interface and one or more concrete implementations. New providers in an area are an isolated file change. New areas are a new directory.
- **Governance** (`nba_platform/governance/`). Audit, budget, and approval primitives. Audit emits structured events; budget tracks per-agent spend with a configurable headroom factor; approval routes pre-write proposals to a CRM-backed Approvals queue.
- **Evals** (`nba_platform/evals/`). Records per-invocation `EvalRun` rows and `MetricSnapshot` rollups. Per-agent / per-customer / per-vertical aggregation is supported out of the box.
- **Outputs** (`nba_platform/outputs/`). Three renderers: PDF (account one-pagers and long-form reports), Markdown / digest (weekly digests), and XLSX/CSV exporter (pipeline snapshots — the customer-facing artefact for any customer on the spreadsheet-deliverable path). Templates come from the vertical pack; per-customer branding comes from `brand.yaml`.
- **Lib** (`nba_platform/lib/`). The config loader and logging utilities — everything else either consumes a `ConfigBundle` or is part of one.

### Vertical packs (`verticals/<vertical>/`)

The domain knowledge for a class of new-business pipeline — **customer-agnostic but vertical-specific**. A vertical pack contains:

- `schemas/` — field definitions per record kind (target organisation, stakeholder, signal).
- `data_sources/` — registries and trade-press sources the agents consult.
- `ranking/` — fit-score weights and rules.
- `compliance/` — regulatory and trading-practice notes.
- `outputs/` — Markdown templates for one-pagers and digests.
- `README.md` — what the pack is for.

A vertical pack defines the role taxonomy that customer `personas.yaml` files **subset** — customers narrow the vertical taxonomy, they do not extend it. Extensions to the taxonomy are vertical-pack changes that benefit every customer.

### Customer configs (`customers/<customer>/`)

The customer's specifics — **YAML only, no code**. Each customer directory has the same nine files (eight YAML plus a README). The config loader walks the directory, merges in the vertical pack the customer is pinned to, and produces a single `ConfigBundle`. Validation rejects deployment on missing files, malformed YAML, or vertical pinning to a pack that does not exist.

## Substrate options

The CrmAdapter abstraction in `nba_platform/integrations/crm/base.py` is what lets the same agent code persist into different substrates per customer. Three implementations are in the repo, listed in order of pilot-readiness:

| Adapter | Kind | When | Notes |
| :--- | :--- | :--- | :--- |
| `SqliteAdapter` | `sqlite` | Customer has no CRM and wants spreadsheet-only deliverables. The pilot default. | Stdlib only. Single `.db` file in a mounted volume. The XLSX exporter (`nba_platform/outputs/xlsx_exporter.py`) renders state into customer-facing workbooks. |
| `AirtableAdapter` | `airtable` | Customer wants a cloud-hosted shared view of pipeline state. First feature add-on. | Requires the optional dependency group (`pip install -e ".[airtable_substrate]"`) and an Airtable base set up per `ops/airtable_schema.md`. Preferred runtime path is the Airtable MCP server; REST is fallback. |
| `StackOneAdapter` | `stackone` | Customer has a real CRM (Salesforce, HubSpot, Pipedrive, Bullhorn…). | Stub at the time of the pilot — first customer to need this triggers the platform-level build. Same interface, no agent code changes. |

Substrate swaps are a `crm.yaml` `kind` flip plus a one-time data migration. The first customer to switch substrates is also the trigger to land the migration helper in `nba_platform/lib/`.

## The flow on one wake

When an agent is woken by Paperclip:

1. Paperclip injects the agent's SKILL.md as the system prompt.
2. The agent calls into `platform.lib.config_loader.load_customer_bundle(customer)` to get the `ConfigBundle`.
3. The agent reads its specific config slice from the bundle — for example, the Outreach Drafter reads `bundle.brand`, `bundle.personas`, and the relevant compliance file from `bundle.vertical_pack`.
4. The agent calls adapters via the abstract interface — `CrmAdapter.upsert`, `EnrichmentAdapter.find_contact`, `LLMAdapter.complete` — never a concrete provider directly.
5. The agent emits audit events via `platform.governance.audit`. Budget checks happen before LLM calls; approval routing happens at write time.
6. The eval harness records the invocation for the per-agent / per-customer rollup.

## Adding things — discipline summary

| Adding... | Where it lands | Layers touched |
| :--- | :--- | :--- |
| A new customer in an existing vertical | `customers/<new>/` only | Customer only |
| A new vertical pack | `verticals/<new>/` and the placeholder removed | Vertical only |
| A new integration provider in an existing area | `nba_platform/integrations/<area>/<new>.py` | Platform only |
| A new integration area (e.g. payments) | `nba_platform/integrations/<area>/` new directory | Platform only |
| A new agent role | `nba_platform/agents/<new>/SKILL.md` + Paperclip company template entry + `agents.yaml` entry in every customer | Platform + ops + customer |
| A new field on an existing record kind | `verticals/<vertical>/schemas/<kind>.yaml` + adapter mapping | Vertical (+ ops/airtable_schema.md if Airtable is used) |
| A new signal kind | `verticals/<vertical>/schemas/signal.yaml` | Vertical only |
| Brand-voice change for a customer | `customers/<customer>/brand.yaml` | Customer only |

The repository's QA script (`scripts/qa.py` / `nba-qa`) enforces all of this on every run.
