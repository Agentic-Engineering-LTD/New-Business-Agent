# Compliance — retail trading & data protection

This document is read by the **Outreach Drafter** (compliance footer rules), the **Contact Enricher** (data-protection limits), and the **Hand-off** agent (digest disclaimers). Customer-specific overrides live in `customers/<customer>/thresholds.yaml`; this file is the floor, not the ceiling.

## UK GDPR / EU GDPR — personal-data handling

The platform writes stakeholder records that contain personal data (name, work email, work phone, job title). The following rules apply to every customer pinned to this vertical.

### Lawful basis

The default lawful basis for writing a stakeholder record is **legitimate interests** — the customer has a commercial interest in identifying decision-makers at target organisations for B2B outreach. This basis is appropriate ONLY where:

- The contact is being approached in a clearly business capacity (work email, work phone, business role).
- The role band is a buying-line or licensing-line role plausibly responsible for the customer's category.
- No special-category personal data is collected (health, beliefs, etc. — irrelevant to this pipeline and explicitly prohibited).

### Personal contact details — opt-in only

The **Contact Enricher** must NOT write personal-mobile or personal-email fields to stakeholder records unless the customer's `thresholds.yaml` explicitly opts in via `enrichment.allow_personal_contact: true`. Default is `false`.

### Right-to-object footer

Every outbound draft produced by the **Outreach Drafter** for an EU/UK recipient must include an opt-out footer. The default text (override per customer in their `brand.yaml`):

> If you would prefer not to receive future emails from {customer_legal_name}, reply with "unsubscribe" and we will remove you from our outreach list.

### Data minimisation

The Refresh / Watch agent's stale-record handling exists to honour data minimisation. A stakeholder record marked `freshness_band: stale` for longer than the customer's `thresholds.freshness.stakeholder_archive_after_days` (default 365) is moved to an archived state — not deleted (audit trail is preserved), but removed from active pipeline.

## UK retail trading — sensitivity windows

The **Hand-off** agent's weekly digest and the **Outreach Drafter**'s drafts should observe trading-sensitive windows. These are guidance, not hard blocks:

- **Pre-Christmas (Oct–Dec).** UK retailers' buying teams are heads-down on peak trading. Strategic conversations land badly; tactical conversations (samples, fast-turn ranges) land fine. The digest should reflect this.
- **Pre-AW / SS buying meetings.** When a retailer's public calendar shows imminent buying meetings for a season, the Outreach Drafter should default to `signal_hook` over `category_fit_hook`.
- **Post-results blackout.** Listed retailers' buying teams are quieter in the two weeks before and one week after annual / interim results. Avoid cold-touch in that window.

## Non-disclosure / NDA handling

The platform does not store NDA-covered information about a target. If a fact is supplied by the customer that is NDA-covered, it goes in `customers/<customer>/targets.yaml` under `private_intelligence` and is rendered only into outputs delivered to that customer — never logged, never quoted in drafts, never shared between customers.

## Things the agents must never do

- Scrape LinkedIn, ever. This is a platform-wide rule but is restated here because LinkedIn data on individuals is a common compliance pitfall in B2B outreach pipelines.
- Reproduce verbatim more than a short quote from trade-press content (default cap: 15 words) in any signal record, digest, or draft. Summaries are in the agent's own words.
- Use a personal mobile number obtained through enrichment to leave voicemail / SMS. Outbound to personal numbers is out of scope for this pipeline.
