# Platform layer

Industry-agnostic. **Nothing in this directory may reference vertical-specific or customer-specific terms** (industry names, customer names, named target archetypes, role-band labels). If you find yourself reaching for one, the right home is `verticals/<vertical>/` or `customers/<customer>/`. The repo-wide QA script (`scripts/qa.py`) enforces this.

## What lives here

| Directory | Purpose |
| :--- | :--- |
| `agents/` | One `SKILL.md` per agent role. Paperclip injects these at runtime. The skills reference vertical-pack and customer-config inputs by interface, not by name. |
| `integrations/` | Adapters for every external system: CRM, LLM, enrichment, web search. Each adapter sits behind a clean interface even when there is only one implementation today. |
| `governance/` | Approval gates, budget caps, audit-trail helpers. Hooks into Paperclip's native governance. |
| `evals/` | Per-agent and per-customer eval harness — success rate, latency, cost, draft approval rate, stakeholder resolution accuracy. |
| `outputs/` | Output rendering engine — PDF, weekly digest, account one-pager. Templates supplied by the vertical pack; brand assets by the customer config. |
| `lib/` | Shared utilities — config loader, structured logging, common types. |

## The eight agent roles

Each agent has a directory at `agents/<agent>/` with a `SKILL.md` and (optionally) supporting files. The agent's *behaviour* in any given deployment is the union of:

1. The platform SKILL.md (this layer) — what the agent does, generically
2. The vertical pack (`verticals/<vertical>/`) — schemas, sources, ranking rules, output templates
3. The customer config (`customers/<customer>/`) — target list, brand, personas, thresholds, CRM credentials

Agents NEVER hard-code a customer's specifics. If a customer needs different behaviour, it goes in their config or — if it generalises — in the vertical pack.

## Adapter discipline

Every external system lives behind an interface in `integrations/<area>/base.py`. Implementations sit alongside in the same directory. This is non-negotiable even when there is only one implementation today, because:

- It keeps agent code readable (one named interface, not a tangle of vendor SDKs).
- It makes vendor swaps a configuration change, not a code change. A customer starting on Airtable and graduating to a real CRM later is exactly this story.
- It makes tests cheap (mock the interface, not the SDK).

## What this layer does NOT contain

- Industry-specific schemas (those are in vertical packs).
- Customer brand assets, target lists, persona definitions (those are in customer configs).
- Hard-coded credentials, API keys, or environment-specific values (those are in Paperclip instance secrets).
