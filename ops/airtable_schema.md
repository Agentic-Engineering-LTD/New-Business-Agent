# Airtable base schema — feature add-on (not in pilot scope)

> **Status: Not enabled for PowerPlay's pilot.** PowerPlay's deliverable
> is XLSX/CSV files and persistence is SQLite — see
> `customers/powerplay/crm.yaml`. This document is preserved because
> Airtable is the **first available feature add-on** when a customer
> wants a cloud-hosted shared view of pipeline state. To enable for a
> customer, flip their `crm.yaml` `kind` to `airtable`, set up the base
> as described below, and install the optional dependency group:
>
>     pip install -e ".[airtable_substrate]"
>
> The `AirtableAdapter` (`nba_platform/integrations/crm/airtable.py`) is
> the reference implementation; the Airtable MCP server is the
> preferred runtime path once the base exists.

This is the structure a customer's Airtable base must have **before the first agent wakes if Airtable is enabled**. The `AirtableAdapter` and the Airtable MCP server both assume these tables exist with these field names.

Customers without an incumbent CRM may also graduate to a real CRM via the StackOne adapter later, at which point the field shape below maps directly onto the StackOne-mapped fields instead.

## Tables

### Targets

The `target_organisation` records. Natural key: `domain`.

| Field | Type | Notes |
| :--- | :--- | :--- |
| `legal_name` | Single line text | Required |
| `trading_name` | Single line text | |
| `domain` | Single line text | **Natural key** — set as primary field |
| `registered_number` | Single line text | |
| `hq_country` | Single select | ISO 3166 alpha-2 (GB, IE, DE, FR…) |
| `hq_region` | Single line text | |
| `store_count_band` | Single select | <50 / 50-200 / 200-1000 / 1000-5000 / >5000 / online_only |
| `banner_brands` | Multiple select | |
| `categories_carried` | Multiple select | |
| `revenue_band` | Single select | <£10m / £10m-£50m / £50m-£250m / £250m-£1bn / >£1bn / unknown |
| `parent_group` | Single line text | |
| `fit_score` | Number | 0–100, written by the Opportunity Assessor |
| `fit_band` | Single select | hot / warm / watch / parked |
| `source_provenance` | Long text | JSON array (the adapter serialises a list-of-objects to JSON for storage) |
| `last_checked_at` | Date & time | Maintained by the Refresh / Watch agent |
| `freshness_band` | Single select | fresh / aging / stale |
| `created_at` | Created time | Airtable-managed |
| `updated_at` | Last modified time | Airtable-managed |

### Stakeholders

The `stakeholder` records. Natural key: `work_email`. Linked to **Targets**.

| Field | Type | Notes |
| :--- | :--- | :--- |
| `full_name` | Single line text | |
| `first_name` | Single line text | |
| `last_name` | Single line text | |
| `work_email` | Email | **Natural key** — set as primary field |
| `direct_phone` | Phone number | |
| `role_title` | Single line text | Verbatim from enrichment |
| `role_band` | Single select | Values match `verticals/brand_licensing_b2b/schemas/stakeholder.yaml` |
| `reports_to` | Single line text | |
| `target_organisation` | Link to another record | → **Targets** |
| `confidence_band` | Single select | high / medium / low |
| `freshness_band` | Single select | fresh / aging / stale |
| `last_verified_at` | Date & time | |
| `source_provenance` | Long text | JSON array |
| `created_at` | Created time | |
| `updated_at` | Last modified time | |

### Signals

The `signal` records. Natural key is composite: `(target, source_url, signal_kind, observed_date)`. Linked to **Targets**.

| Field | Type | Notes |
| :--- | :--- | :--- |
| `signal_id` | Formula or autonumber | Primary field |
| `signal_kind` | Single select | Values match `verticals/brand_licensing_b2b/schemas/signal.yaml` |
| `target_organisation` | Link to another record | → **Targets** |
| `observed_date` | Date | |
| `source_url` | URL | |
| `source_publication` | Single line text | |
| `headline` | Single line text | |
| `summary` | Long text | Agent's own words — never verbatim source content |
| `relevance` | Single select | critical / high / medium / low |
| `created_at` | Created time | |

### Activities

The `activity` records — outreach drafts, recommendations, one-pager requests. Linked to **Targets** and **Stakeholders**.

| Field | Type | Notes |
| :--- | :--- | :--- |
| `activity_id` | Formula or autonumber | Primary field |
| `kind` | Single select | outbound_draft / one_pager_request / recommendation / note |
| `target_organisation` | Link to another record | → **Targets** |
| `stakeholder` | Link to another record | → **Stakeholders** (optional) |
| `status` | Single select | pending_review / approved / rejected / sent_externally / closed |
| `hook` | Single line text | For outbound_draft: signal_hook / category_fit_hook / relationship_hook |
| `subject` | Single line text | For outbound_draft |
| `body` | Long text | For outbound_draft, also used by recommendations |
| `cited_signal` | Link to another record | → **Signals** (optional) |
| `created_by_agent` | Single select | Which agent wrote this record |
| `created_at` | Created time | |
| `updated_at` | Last modified time | |

### Approvals

The HITL gate. When a write has `require_approval: true` for its record kind, the adapter writes here instead of the target table. A human reviewer approves or rejects; on approve, the platform replays the write to the real table.

| Field | Type | Notes |
| :--- | :--- | :--- |
| `approval_id` | Formula or autonumber | Primary field |
| `record_kind` | Single select | target_organisation / stakeholder / signal / activity |
| `proposed_payload` | Long text | JSON blob of the record the agent wanted to write |
| `natural_key` | Single line text | The natural key value of the proposed record |
| `requesting_agent` | Single select | Which agent requested the write |
| `status` | Single select | pending / approved / rejected |
| `reviewer` | Collaborator | Set on resolution |
| `decided_at` | Date & time | Set on resolution |
| `notes` | Long text | Reviewer rationale |
| `created_at` | Created time | |

## Notes for the setup operator

- Use Airtable's **Personal Access Token (PAT)** as the credential, not the deprecated API key. Scope: read + write on the base, no schema-mutation scope needed once tables exist.
- The adapter creates records via the REST API where the MCP server's `create_record` tool is not used; both paths assume the field names above exactly.
- Single-select option values must match the YAML enums in `verticals/brand_licensing_b2b/schemas/*.yaml`. Mismatches are caught by the QA script (`scripts/qa.py`).
- The natural-key fields (`domain` for Targets, `work_email` for Stakeholders) should be the **primary field** of each table — Airtable's primary field is the human-readable record handle.
