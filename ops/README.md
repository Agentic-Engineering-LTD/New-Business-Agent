# Ops

Operational artefacts for running this repo against a live Paperclip instance.

## What's here

| File | Purpose |
| :--- | :--- |
| `paperclip_company_template.yaml` | Importable Paperclip *company* definition — org chart of agents, adapter configs, monthly budgets, top-level goal. Adapt per customer. |
| `deployment.md` | How the dockerised Paperclip instance runs on the shared Hostinger UK VPS — volumes, secrets, scheduling, health checks. |
| `airtable_schema.md` | Airtable base structure for customers who opt into the Airtable substrate add-on. Not required for the pilot. |

## What is not here

- **Secrets.** Never. Secrets live in Paperclip's secrets store and are referenced by name only.
- **Customer-specific data.** That lives in `customers/<customer>/`.
- **Platform code.** That lives in `nba_platform/`.

## Substrate choice for a new customer

| Substrate | When to use | What to do |
| :--- | :--- | :--- |
| **SQLite + XLSX/CSV deliverable** *(pilot default)* | Customer has no CRM and wants spreadsheet-only output. Fastest to set up. | Set `kind: sqlite` in their `crm.yaml`. Configure `output_dir` and snapshot cadence in `outputs.yaml`. No external schema setup needed. |
| **Airtable** *(feature add-on)* | Customer wants a cloud-hosted shared view of pipeline state without committing to a real CRM yet. | Set `kind: airtable` in their `crm.yaml`. Install with `pip install -e ".[airtable_substrate]"`. Set up the Airtable base per `airtable_schema.md`. Wire the `AIRTABLE_PAT` secret in Paperclip. |
| **StackOne (real CRM)** | Customer has an existing CRM — Salesforce, HubSpot, Pipedrive, Bullhorn etc. | Set `kind: stackone` in their `crm.yaml`. Configure the StackOne connector for the specific CRM. Implementation lives in `nba_platform/integrations/crm/stackone.py` (stub at the time of the pilot — first customer to need this triggers the platform-level build). |
