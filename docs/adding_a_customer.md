# Adding a customer

A customer is one deployment of the platform in one vertical. Adding one is **YAML only** — no Python should be necessary.

## Prerequisites

Before opening the editor:

- The customer is pinned to an **already-populated** vertical pack. (If they need a new vertical, see `docs/adding_a_vertical.md` first.)
- You have the customer's brand voice, signature block, and licensed-property / portfolio summary.
- You know the customer's CRM substrate — Airtable (no existing CRM), or a real CRM via StackOne.
- You know their geographies, channels, and target-archetype shape.
- You know their persona subset — which role bands from the vertical taxonomy do they care about?
- You have the customer's pilot success metrics — what does "this is working" look like at week 12?

## Steps

1. **Create the directory.** `customers/<customer_key>/`. Use a lowercase, hyphen-free key — it appears in audit events, output filenames, and CLI commands.

2. **Write the README.** Pilot scope, deployment summary (CRM, calibration window, hosting), first-run prerequisites.

3. **Write `company.yaml`.** Three lines: `name`, `vertical`, `timezone`. The `vertical` value must exactly match a directory under `verticals/`.

4. **Write `targets.yaml`.** What does a good target look like for this customer? Geographies in scope, channels in scope, retailer archetypes, deal-size profile, any non-compete restrictions.

5. **Write `brand.yaml`.** Voice notes, forbidden phrases, signature block, opt-out footer, logo paths, colour palette, typography. The Outreach Drafter and PDF renderer read this.

6. **Write `personas.yaml`.** Subset the vertical's role taxonomy — list only the `role_band` values this customer cares about. Define a seniority priority order. Set `minimum_confidence_band_to_action`.

7. **Write `thresholds.yaml`.** Confidence bands, freshness windows, fit-score weight overrides (often empty during calibration), outreach throttles, budget caps per agent, approval-queue thresholds.

8. **Write `crm.yaml`.** Substrate `kind`, plus the substrate-specific config. Three options:
   - `kind: sqlite` — pilot default. Specify `db_path` (a filesystem path inside the container volume), the `tables` map, the `natural_keys` map, and the `require_approval` map. Nothing external to set up.
   - `kind: airtable` — feature add-on. Install with `pip install -e ".[airtable_substrate]"`. Set up the Airtable base per `ops/airtable_schema.md`. Specify `base_id`, `pat_secret_name`, the table mappings, and the `require_approval` map.
   - `kind: stackone` — for customers with a real CRM. Configure the StackOne connector per the StackOne docs for that CRM. Same `require_approval` semantics.
   Default to gating stakeholder writes during the first six weeks regardless of substrate — calibration discipline is substrate-independent.

9. **Write `outputs.yaml`.** Weekly digest cadence and recipients, account one-pager triggers, refresh schedule, outreach throttles.

10. **Write `agents.yaml`.** Which agents are enabled. New customers default `proactive_recommender: false` and `outreach_drafter: false` (then graduate the drafter on once enrichment is calibrated).

11. **(If CRM is Airtable) Set up the Airtable base** to match `ops/airtable_schema.md`. Run `python scripts/bootstrap_<customer>.py` or copy `bootstrap_powerplay.py` as a starting point.

12. **Import the Paperclip company definition.** Copy `ops/paperclip_company_template.yaml` and adjust the `customer_id`, budgets, and goal. Import via the Paperclip UI.

13. **Run the QA script.** It loads every customer config in the repo through the validator. A failure here usually means a missing file, a typo in a vertical name, or a persona-subset value not in the vertical taxonomy.

14. **Run the bootstrap script** (or its customer-specific variant) before waking any agent. It probes the CRM substrate for reachability and confirms the table structure.

15. **Wake agents one at a time.** Start with `target_identifier`. Observe the Approvals queue. Do not enable `outreach_drafter` until at least 10 stakeholder approvals have been processed cleanly.

## Time to first wake

The first customer (PowerPlay) was a green-field exercise alongside the platform build — call it a fortnight of total effort split across both. Subsequent customers in the same vertical should compress significantly:

- Customer 2 in Brand Licensing B2B: 3–5 days, dominated by Airtable setup and brand-voice tuning.
- Customer 3+: 2–3 days, dominated by the customer-supplied content (targets, personas, brand).

## Anti-patterns

- **Editing a vertical pack to suit one customer.** If a customer needs a role band the vertical doesn't have, either subset more aggressively or — if the role is genuinely vertical-wide — extend the vertical pack and benefit every customer.
- **Putting customer code in the customer directory.** Customer configs are YAML only. If logic is needed, it belongs in the platform or in an adapter, behind an interface.
- **Skipping calibration.** The Approvals queue exists for a reason. Customers who skip the calibration window end up with stakeholder records of unknown quality and outreach drafts the commercial team won't trust.
