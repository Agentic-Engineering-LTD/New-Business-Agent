# Adding a vertical pack

A vertical pack is the domain knowledge for a class of new-business pipeline. Adding one is **bounded to its own directory** — no platform-level changes should be required.

## Prerequisites

Before opening the editor, get clear on:

- The target organisation's primary identifier (`domain`? `registered_number`? `ticker`?). This becomes the natural key.
- The stakeholder role taxonomy — every buying-line, decision-making role the pipeline cares about. Bounded vocabulary, not a free-text field.
- The signal taxonomy — the events that mean "something is happening here". Bounded.
- The data sources the agents will read (registries, trade press, public filings).
- The fit-score criteria and rough weight ordering.
- The compliance regime (GDPR, FCA, MHRA, sector-specific).
- The output templates the customer wants — what does a one-pager say in this vertical? What does the weekly digest look like?

## Steps

1. **Mirror the structure.** Copy `verticals/brand_licensing_b2b/` as a template:
   ```
   verticals/<new_vertical>/
     README.md
     schemas/
       target_organisation.yaml
       stakeholder.yaml
       signal.yaml
     data_sources/
       *.yaml
     ranking/
       fit_score.yaml
       rules.md
     compliance/
       *.md
     outputs/
       account_one_pager.template.md
       weekly_digest.template.md
   ```

2. **Write `schemas/target_organisation.yaml`.** Decide the natural key. List all required and optional fields. Use enums for any field where the value space is bounded (size bands, regions, channels). Avoid free-text where a controlled vocabulary will do.

3. **Write `schemas/stakeholder.yaml`.** This is the role taxonomy. The `role_band` enum is what customers will subset in their `personas.yaml`. Keep the band names canonical and avoid customer-specific titles.

4. **Write `schemas/signal.yaml`.** Define each `signal_kind` with a relevance default, the typical source channels, and a `dedupe_window_days`. The Refresh / Watch agent is constrained to these kinds — anything outside the taxonomy is dropped.

5. **Write `data_sources/*.yaml`.** One file per category of source (registries, trade press, regulatory filings). Each source declares its access mode (free / paywall / subscription), the signal kinds it supplies, and any API secret name.

6. **Write `ranking/fit_score.yaml` and `ranking/rules.md`.** The YAML is numeric weights summing to 1.0; the MD is plain-English disqualifiers, promoters, demoters, and manual-review flags. Both are read by the Opportunity Assessor.

7. **Write `compliance/*.md`.** What regulations apply? What footer language? What's the lawful basis for personal-data writes? Be explicit — the agents read these and the customer's compliance officer should be able to.

8. **Write the output templates.** Jinja2 syntax. The renderer in `nba_platform/outputs/` substitutes the customer's brand assets at render time.

9. **Write the README.** What the pack is for, what's in it, what does not belong here.

10. **Run the QA script.** It validates structural completeness — that every section is present and every section is populated. A placeholder vertical (README only) is excused; a partly-populated one fails.

## Anti-patterns

- **Customer-specific data in a vertical pack.** A specific retailer's name, a customer's licensed-property list, a customer's signature block. Those belong in `customers/<customer>/`.
- **Platform-specific changes for one vertical.** If a vertical seems to need a new agent or a new integration, the platform layer is the place to add it — every vertical benefits.
- **Open-ended fields where an enum will do.** Free-text signal kinds, free-text role titles. They break the dedup logic and they break the Outreach Drafter's tone matching.
- **Forking an existing vertical pack rather than extending it.** If two verticals look 80% the same, they probably should be one pack with the differences in customer configs. Forking creates two copies of the same maintenance.

## Cost expectations

The first vertical pack (Brand Licensing B2B) took roughly the same shape as a green-field design exercise — ~1 week of domain work, ~2 days of authoring. Subsequent verticals should compress dramatically: the structure is fixed, the patterns are copyable, and the only original work is the domain content itself. Target for vertical N+1: 2–3 days of domain work, ~1 day of authoring.
