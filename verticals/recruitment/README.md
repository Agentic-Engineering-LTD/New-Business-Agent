# Vertical pack — Recruitment (placeholder)

This directory is a **scaffold-only placeholder** for the Recruitment vertical pack. The platform is intentionally multi-vertical from day one — including this skeleton commits the platform to that discipline at the source tree level, not just the README.

## Status

- **Not populated.** No schemas, data sources, ranking, or output templates are present here yet.
- **Not loadable.** Any customer pinned to `vertical: recruitment` in their `company.yaml` will fail config validation with a missing-pack error. This is by design — it prevents accidentally deploying a half-built vertical.

## Who fills this in

The Eligo engagement is the first customer for this vertical. The Recruitment pack lands when that engagement defines:

- The target organisation schema (a recruitment client — agency? in-house TA? RPO?).
- The stakeholder role taxonomy (Talent Director, Head of TA, Recruitment Manager, Hiring Manager line, etc.).
- The signal taxonomy (funding round, headcount growth, new office opening, exec hire of a CHRO, etc.).
- The data sources (recruitment-trade press, Companies House, funding databases).
- The fit-score weights.
- The compliance notes (recruitment-industry-specific data handling).
- The digest and one-pager templates.

## Structure to follow

When populated, this pack must mirror `verticals/brand_licensing_b2b/`:

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
    README.md

The platform code is vertical-agnostic — adding this pack requires zero changes outside this directory.
