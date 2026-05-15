# Paperclip setup

This document explains how the platform sits on top of Paperclip (paperclip.ing) — what Paperclip provides, what the platform provides, and how the two integrate.

## What Paperclip is, in our terms

Paperclip is a **control plane**, not an agent framework. It does not tell us how to build agents. It tells us how to run a company made of them.

What Paperclip owns:

- **Companies** — one per customer deployment.
- **Agents as heartbeats with adapter configs** — Paperclip wakes them on a schedule or trigger, hands them their skill, and tracks their lifetimes. The runtime is external (Claude Code, a Python script behind a webhook, an MCP runtime).
- **Skills injected at runtime** — the SKILL.md files in `nba_platform/agents/` are loaded into agent invocations as the system prompt.
- **Goals** — declarative outcomes the company optimises for.
- **Tickets** — units of work flowing between agents.
- **Budgets** — per-agent monthly USD caps with approval gates.
- **Governance primitives** — audit log, approval queue surfacing.
- **MCP server registry** — Paperclip's catalogue of connected MCP servers, including the Airtable MCP server we use.

What Paperclip does **not** own:

- The skill content — that's ours, in `nba_platform/agents/`.
- The integration adapters — those are ours, in `nba_platform/integrations/`.
- The record schemas, ranking, output templates — those are vertical-pack content.
- Customer configuration — that's customer YAML.

## Setting up a customer's Paperclip company

1. **Spin up the container** — see `ops/deployment.md` for the dockerised setup on the shared VPS.

2. **Import the company template.** Take `ops/paperclip_company_template.yaml`, replace the `customer_id` with the customer's key, confirm budgets match the customer's `thresholds.yaml`, and import via Paperclip's UI.

3. **Wire secrets.** In Paperclip's secrets pane, register the keys this repo's YAML files reference by name:
   - `AIRTABLE_PAT`
   - `OPENROUTER_API_KEY`
   - `COGNISM_API_KEY`
   - `TAVILY_API_KEY`
   - `COMPANIES_HOUSE_API_KEY`
   - (Plus any others added by future integrations.)

   These resolve at runtime — agents read them via `os.environ` inside the container, and Paperclip injects them. No secret should ever appear in repo files.

4. **Enable the Airtable MCP server.** Paperclip's MCP registry has the Airtable MCP server (supplied by Airtable: see `support.airtable.com/docs/using-the-airtable-mcp-server`). Enable it and confirm it's reachable from the customer's company.

   Our agents prefer the MCP path for CRM operations and fall back to the REST adapter in `nba_platform/integrations/crm/airtable.py` for bulk reads and health checks.

5. **Confirm agent runtimes are wired.** Each agent in the company template has a `skill_path` pointing at a SKILL.md and an `adapters` list. Paperclip routes the agent's tool calls through the named adapters; the adapter configurations live in the same company template under `adapter_configs`.

6. **Wake the schedules.** The `refresh_watch` and `hand_off` agents have cron schedules in the company template. Confirm they're enabled in Paperclip's schedule view.

## Skills as the platform's primary product

Most of this repo, in volume, is SKILL.md files and the YAML they read. The Python in `nba_platform/` is a thin support layer: adapters, eval harness, output rendering, config loading. We do **not** build a bespoke "agent framework" in Python — Paperclip is the framework, and we contribute skills and adapters.

That discipline is what makes the platform composable. Adding an agent is a SKILL.md plus an entry in the Paperclip company template plus an entry in every customer's `agents.yaml`. Adding an adapter is one file in `nba_platform/integrations/<area>/`. Adding a customer is YAML. Adding a vertical is one directory of YAML and Markdown.

## MCP integration patterns

Two paths to external systems, in priority order:

1. **MCP server (preferred).** If the external system has an MCP server (Airtable, GitHub, Notion, Slack), Paperclip's MCP integration is the path. The skill mentions tool capabilities at the abstract level; Paperclip resolves them against connected servers.

2. **Adapter (fallback / specialist).** When the MCP server doesn't expose the operation efficiently (bulk reads, batched writes, health checks), the platform's adapter in `nba_platform/integrations/<area>/<provider>.py` handles it. The skill calls the same abstract interface either way.

For PowerPlay, this means: most stakeholder lookups and writes go through the Airtable MCP server; the Refresh / Watch agent's full-base scans and the platform's health check go through the REST adapter.
