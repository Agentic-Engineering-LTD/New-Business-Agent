# New Business Agent

The productised platform for autonomous market entry and stakeholder identification — built by [Agentic Engineering Ltd](https://agenticengineering.co.uk).

This repository is the canonical home of the **New Business Agent** platform, its **vertical packs**, and per-customer deployment configurations. It is an early-stage build under active customer engagement; the architecture is deliberately structured to scale across many customers without re-implementation.

## Architecture in three layers

| Layer | Lives in | Reuse scope | Examples |
| :--- | :--- | :--- | :--- |
| **Platform** | `nba_platform/` | Every customer in every vertical | Agent skills, integration adapters, governance, eval harness, output engine |
| **Vertical pack** | `verticals/<vertical>/` | Every customer in that vertical | Industry schemas, signal sources, ranking rules, compliance, output templates |
| **Customer config** | `customers/<customer>/` | One customer | Target list, brand assets, personas, thresholds, CRM credentials, output cadence |

The discipline that makes this work:

- **No vertical or customer specifics in `nba_platform/`.** Platform code never references industry-specific or customer-specific terms. Agents take their behaviour from the vertical pack + customer config injected at runtime. The QA script (`scripts/qa.py`) enforces this.
- **Vertical packs are customer-agnostic.** The Brand Licensing B2B pack works for any apparel-licensing customer; the Recruitment pack works for legal, finance, life sciences recruitment specialisms, not just Eligo's datacenter focus.
- **Customer config is configuration, not code.** Target lists, persona definitions, ranking thresholds, brand voice — all YAML, no Python.

If you find yourself about to put a customer-specific or vertical-specific string in the platform layer, stop. Either it belongs in a vertical pack, in customer config, or it doesn't belong at all.

## Current state

| Vertical | Status | Design partner |
| :--- | :--- | :--- |
| Brand Licensing B2B | Active build | PowerPlay Brands |
| Recruitment | Scaffolded, parallel engagement | Eligo (datacenter recruitment) |

| Customer | Vertical | Status |
| :--- | :--- | :--- |
| `powerplay` | Brand Licensing B2B | Pilot — Phase 0 sandbox |
| `eligo` | Recruitment | Parallel engagement — separate solution design |

## The eight platform agents

| # | Agent | Status | Notes |
| :--- | :--- | :--- | :--- |
| 1 | Target Identifier | Implemented | Finds in-scope target organisations |
| 2 | Organisation Mapper | Implemented | Maps decision-maker structures within each target |
| 3 | Contact Enricher | Implemented | Verifies and enriches named decision-makers |
| 4 | Opportunity Assessor | Implemented | Scores fit + writes structured rationale |
| 5 | Hand-off Agent | Implemented | Persists state via the CRM adapter; renders deliverables (XLSX/CSV snapshot, weekly digest, account one-pager); applies decisions from `approvals_inbox.csv` |
| 6 | Refresh / Watch | Implemented | Surfaces deltas and new signals |
| 7 | Outreach Drafter | Implemented (PowerPlay: on; Eligo: off) | Drafts intro + follow-up sequences |
| 8 | Proactive Recommender | Interface only | Synthesises pipeline state into "next actions" — future cycle |

Each agent's behaviour is defined by a `SKILL.md` file at `nba_platform/agents/<agent>/SKILL.md`. Paperclip injects these at runtime per the [Paperclip skills convention](https://github.com/paperclipai/paperclip).

## Technology choices

- **Orchestration:** [Paperclip](https://github.com/paperclipai/paperclip) — control plane (companies, agents, goals, tickets, budgets, governance, skills). One Paperclip instance per customer, dedicated VPS.
- **LLM access:** [OpenRouter](https://openrouter.ai) — Claude Sonnet 4.6 (reasoning-heavy agents) and Claude Haiku 4.5 (high-frequency lightweight tasks). BYOK per customer.
- **Persistence substrate:** SQLite (stdlib-only) by default — a single `.db` file in the container volume. Airtable is the first feature add-on for customers wanting a cloud-hosted shared view; [StackOne MCP](https://stackone.com) (270+ connectors) handles real CRMs. All three sit behind the same `CrmAdapter` interface — substrate swaps are a `crm.yaml` flip.
- **Customer deliverables:** XLSX + CSV pipeline snapshots, markdown/email weekly digest, on-demand account one-pager PDFs.
- **Contact enrichment:** [Cognism](https://www.cognism.com) — UK-headquartered, GDPR-positioned. BYOK per customer.
- **Hosting:** Hostinger UK VPS, one dedicated instance per customer.

## What this is NOT

- **Not an agent framework.** Paperclip is the control plane. We don't reimplement its primitives. SKILL.md files and configuration carry the weight.
- **Not multi-tenant runtime.** Each customer gets a dedicated Paperclip instance on a dedicated VPS.
- **Not auto-onboarding.** Each new customer is a build cycle. Target compression is 2–5 days by customer 3+.
- **Not a customer self-service UI.** All configuration is YAML, edited by Agentic Engineering with the customer in the loop.

## Onboarding PowerPlay (this deployment)

1. Provision UK VPS, install Paperclip per its onboarding guide.
2. Create the data + output volume directories per `ops/deployment.md` (`data/powerplay/` and `data/powerplay/outputs/`).
3. Set environment secrets in Paperclip (OpenRouter API key, Cognism API key, Tavily API key, Companies House API key).
4. Import the Paperclip company template at `ops/paperclip_company_template.yaml`.
5. Run `scripts/qa.py` to validate config and platform/vertical/customer separation.
6. Run `scripts/bootstrap_powerplay.py` to initialise the SQLite schema and verify volume mounts.
7. Wake the Target Identifier agent — first sweep produces a draft target list for human review before any further agents are activated.

See [`docs/paperclip_setup.md`](docs/paperclip_setup.md) for full setup. See [`docs/adding_a_customer.md`](docs/adding_a_customer.md) for the pattern when onboarding customer 3+.

## Licence

MIT with retained copyright by Agentic Engineering Ltd. See [`LICENSE`](LICENSE). Customers receive the codebase with the right to use, modify, and self-host for their own commercial purposes; Agentic Engineering retains the copyright and the right to deploy the platform code to other customers in any industry.

## Build discipline (carry these into any change)

When a request comes in, classify it before writing code:

- **Platform improvement** — benefits all customers in all verticals
- **Vertical pack improvement** — benefits all customers in that vertical
- **Customer-trivial** — small edit to `customers/<name>/` config
- **Customer-bespoke** — meaningful work specific to one customer; flag for separate scoping
- **Not in scope** — flag honestly

Most asks are one of the first three. The fourth and fifth need deliberate decisions, not silent implementation.
