# Ranking rules — Brand Licensing B2B

This document is the **plain-English contract** for what disqualifies, deprioritises, or promotes a target. It is consumed by the **Opportunity Assessor** as part of its prompt, alongside `fit_score.yaml`. Numeric weights live in the YAML; reasoning rules live here.

## Hard disqualifiers

A target is set to `parked` regardless of its weighted score if any of the following are true:

- The retailer's `hq_country` is not in the customer's `targets.geographies_in_scope`.
- The retailer has publicly entered administration / Chapter 11 / equivalent insolvency within the last 90 days.
- The retailer is owned by, or has an exclusive partnership with, a brand owner the customer has a contractual non-compete against (where the customer has supplied a non-compete list in `customers/<customer>/targets.yaml`).
- The retailer has `online_only` as its `store_count_band` AND the customer's `targets.channels_in_scope` does not include online-only retailers.

## Strong promoters

A target gets a one-band promotion (e.g. `warm` → `hot`) if **any one** of:

- There is a `rfp_issued` signal in the last 30 days against this target with `relevance: critical`.
- There is an `exec_change` signal in the last 14 days where the new exec sits in a buying-line `role_band` (buying_director, head_of_category, head_of_licensing).
- There is a `category_expansion` signal in the last 60 days that names a category the customer is licensed to supply.

A target gets a one-band promotion (capped at `hot`) if **two or more** of:

- A `range_launch` signal in the last 90 days.
- A resolved buying-line stakeholder at `confidence_band: high`.
- White space ≥ 0.6 (the retailer carries less than 40% of the customer's category set).

## Strong demoters

A target gets a one-band demotion if **any** of:

- All resolved stakeholders are `freshness_band: stale` and the Refresh / Watch agent has tried to re-enrich them within the last 60 days without success.
- The retailer has had a `partnership_announcement` with a directly competing brand portfolio inside the last 90 days.
- No signals of any kind have been observed against this target in the last 180 days.

## Manual-review flags

The Opportunity Assessor must flag (not auto-band) targets where:

- The retailer is a parent group with operating banners that pull in conflicting directions (some banners in-scope, some out-of-scope).
- The retailer has had `>3` `exec_change` signals against buying-line roles in 12 months — possible org instability the operator may want to consider.
- The fit score and signal freshness disagree strongly (high fit, no recent signals or vice versa).

## Things the assessor must not do

- Do not invent signal-strength estimates from absence of data. "No signals" means no signals — it goes to `signal_freshness` as zero, not as a guess.
- Do not promote on the basis of brand-press content that does not name the retailer or the customer. General industry trends are not target-specific signals.
- Do not auto-band a target above `warm` when no stakeholder of `role_band` in the customer's `personas.yaml` has been resolved. The operator can override, but the agent must not.
