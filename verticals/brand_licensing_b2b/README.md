# Vertical pack — Brand Licensing B2B

This pack encodes the **domain knowledge** for new-business pipelines that sell branded or licensed apparel into B2B retail buyers. It is **customer-agnostic** — any customer pinned to `vertical: brand_licensing_b2b` (in their `company.yaml`) loads this pack at runtime.

It defines:

- Field shapes for the records the platform writes (`schemas/`).
- The retail-trade sources signals come from (`data_sources/`).
- How a target organisation is scored for fit (`ranking/`).
- Regulatory notes the agents must honour (`compliance/`).
- The output templates the **Hand-off** agent uses to render account one-pagers and weekly digests (`outputs/`).

## What lives here

| Section | Purpose |
| :--- | :--- |
| `schemas/target_organisation.yaml` | Fields the **Target Identifier** writes for a retailer. |
| `schemas/stakeholder.yaml` | Fields the **Contact Enricher** writes for an individual; includes the role taxonomy used by the **Organisation Mapper**. |
| `schemas/signal.yaml` | Allowed signal kinds and freshness windows. |
| `data_sources/retail_registries.yaml` | Trusted retailer registries / corporate-information sources (Companies House, FAME, etc.). |
| `data_sources/trade_press_sources.yaml` | Trade-press feeds the **Refresh / Watch** agent monitors for signal events. |
| `ranking/fit_score.yaml` | Weights for the **Opportunity Assessor**'s scoring rubric. |
| `ranking/rules.md` | Plain-English rules the ranking enforces — what disqualifies a target outright, what merits a manual review. |
| `compliance/retail_trading.md` | GDPR and UK/EU retail-trading rules the agents respect when writing records or drafting outreach. |
| `outputs/account_one_pager.template.md` | Markdown template for an account one-pager. |
| `outputs/weekly_digest.template.md` | Markdown template for the weekly digest. |

## What does not live here

- **Customer-specific data** — target geographies, banner brands the customer holds licences for, signature blocks, contract-size bands. Those go in `customers/<customer>/`.
- **Platform code** — adapters, eval harness, governance helpers. Those live in `nba_platform/`.

## When to extend

Adding a new signal kind, a new role to the persona taxonomy, or a new trade-press source benefits every customer pinned to this vertical and should land here. Customer-specific overrides should never be added here; they belong in `customers/<customer>/`.
