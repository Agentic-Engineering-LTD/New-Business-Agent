# Deployment — shared VPS Docker instance

Target environment for PowerPlay's pilot:

- **Host:** Agentic Engineering's shared Hostinger UK VPS.
- **Isolation:** dedicated Docker container per customer. PowerPlay's container is namespaced `paperclip-powerplay`.
- **Control plane:** Paperclip (paperclip.ing) inside the container.
- **Substrate for record-keeping (pilot):** SQLite — a single `.db` file in a mounted volume. See `ops/README.md` for substrate options if a different customer needs Airtable or a real CRM.
- **Customer deliverable (pilot):** XLSX + CSV files in a mounted output volume, accessible to the customer via the digest email's attachments (and optionally over SFTP if requested).

## One-time host prerequisites

1. Docker Engine ≥ 24.0 installed on the VPS.
2. A reverse proxy (Caddy or nginx) terminating TLS at the host; PowerPlay's container listens on an internal port only.
3. Outbound network reachable to: `api.openrouter.ai`, `api.cognism.com`, `api.tavily.com`, `api.company-information.service.gov.uk`, the configured trade-press feeds, and the SMTP relay for digest delivery.
4. Two host directories created and writable by the container user:
   - `/opt/agentic/data/powerplay/` — SQLite database lives here.
   - `/opt/agentic/data/powerplay/outputs/` — XLSX, CSV, PDF deliverables land here.

## Per-customer container setup

1. Clone this repo onto the VPS into `/opt/agentic/new-business-agent/`. Pull updates here; the container mounts this read-only.
2. Create a Paperclip instance for the customer:
   ```bash
   docker run -d --name paperclip-powerplay \
     -v /opt/agentic/new-business-agent:/repo:ro \
     -v /opt/agentic/data/powerplay:/app/data/powerplay:rw \
     -v /opt/agentic/secrets/powerplay:/secrets:ro \
     -p 127.0.0.1:8081:8080 \
     paperclip-ing/paperclip:latest
   ```
3. Import the company definition: in the Paperclip UI for this instance, import `ops/paperclip_company_template.yaml` (or the customer-specific copy if it has been forked into `customers/<customer>/paperclip_company.yaml`).
4. Wire secrets through Paperclip's secrets pane. The names must match those referenced in YAML across this repo:
   - `OPENROUTER_API_KEY`
   - `COGNISM_API_KEY`
   - `TAVILY_API_KEY`
   - `COMPANIES_HOUSE_API_KEY`
   - (Add `AIRTABLE_PAT` only if the customer is on the Airtable substrate add-on.)
5. Run the bootstrap script from outside the container — it talks to the filesystem and Paperclip's API, not the agents:
   ```bash
   uv run python scripts/bootstrap_powerplay.py
   ```
   This validates the SQLite path is writable, the output directory exists, and the Paperclip company definition imports cleanly. It does **not** wake any agent.
6. Wake the agents one at a time, starting with `target_identifier`. Observe the `approvals_inbox.csv` after the first `contact_enricher` wake — the customer needs to populate the `decision` column to release stakeholders into the active pipeline. Do not enable autonomous `outreach_drafter` wakes until at least 10 stakeholder approvals have been processed cleanly.

## Health checks

- The CRM adapter exposes a `health_check()` method. For the SQLite adapter, this probes the database file and reports row counts. Paperclip is configured to run this every 5 minutes; failures trigger an audit event and surface in the next weekly digest's "Health & exceptions" section.
- The LLM adapter rate-limits and tracks per-agent monthly spend. Approaching the 90% budget threshold for any agent triggers an audit event the same way.
- Disk usage on `/opt/agentic/` should be monitored — the eval harness writes JSONL files at `nba_platform/evals/runs/<customer>.jsonl` and these grow without bound. Rotate weekly. The XLSX snapshot files also accumulate; the deployment runbook should add a 90-day retention sweep on `data/<customer>/outputs/`.
- Back up the SQLite file nightly. A simple `cp` while the database is in WAL mode is safe; for a stronger guarantee use `sqlite3 pipeline.db ".backup pipeline_$(date +%F).db"`.

## Updating

1. Pull this repo on the host.
2. Restart the customer's container: `docker restart paperclip-powerplay`.
3. No data migration is required for SKILL.md or YAML changes — Paperclip injects skills at runtime, and config is read on each agent wake.
4. Schema-shape changes to records (e.g. a new field added to the vertical pack's `target_organisation.yaml`) are tolerated by the SQLite adapter because the per-record fields are stored as a JSON blob. New fields appear in subsequent XLSX snapshots automatically.
5. Substrate swaps (SQLite → Airtable, or → a real CRM via StackOne) are a `crm.yaml` change plus a one-time data-migration script. The migration script is not in scope for the pilot; first customer to switch substrates triggers the platform-level migration helper.
