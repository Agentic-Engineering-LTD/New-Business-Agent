"""Bootstrap PowerPlay's deployment — pre-flight checks before the first agent wake.

Run from outside the Paperclip container::

    python scripts/bootstrap_powerplay.py

What it does:

  1. Loads PowerPlay's full config bundle through the platform loader.
     Surfaces any missing files, schema mismatches, or vertical pinning
     problems.
  2. Confirms the configured SQLite ``db_path`` is in a writable
     directory and creates it if missing.
  3. Confirms the configured ``output_dir`` from ``outputs.yaml`` exists
     and is writable.
  4. Initialises the SQLite schema by instantiating the adapter (which
     runs ``CREATE TABLE IF NOT EXISTS`` for every record kind plus the
     approvals table). Idempotent — safe to re-run.
  5. Reports a summary including expected file paths the customer will
     see deliverables at.

What it does NOT do:

  - Touch Paperclip's company definition. Import that through Paperclip's
    UI.
  - Wake any agent.
  - Pre-populate any records.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(2)


async def _run() -> int:
    from nba_platform.integrations.crm import build_crm_adapter
    from nba_platform.lib.config_loader import ConfigError, load_customer_bundle

    print("Bootstrapping PowerPlay deployment...\n")

    # 1. Config bundle
    print("[1/4] Loading customer config bundle...")
    try:
        bundle = load_customer_bundle("powerplay")
    except ConfigError as e:
        _fail(f"config did not load: {e}")
        return 2

    print(f"  customer:        {bundle.customer}")
    print(f"  vertical:        {bundle.vertical}")
    print(f"  agents enabled:  {sorted(n for n, t in bundle.agents.items() if t.enabled)}")
    print(f"  substrate:       {bundle.crm.get('kind')}")
    print()

    # 2. Substrate path checks
    print("[2/4] Checking substrate paths...")
    substrate_kind = bundle.crm.get("kind")
    if substrate_kind != "sqlite":
        _fail(
            f"this bootstrap script assumes substrate kind 'sqlite'; "
            f"got {substrate_kind!r}. Edit customers/powerplay/crm.yaml "
            f"or use the substrate-specific bootstrap for this kind."
        )
        return 2

    db_path = REPO_ROOT / bundle.crm["db_path"]
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.parent.is_dir():
        _fail(f"could not create or access {db_path.parent}")
        return 2
    print(f"  db_path:         {db_path.relative_to(REPO_ROOT)}")
    print(f"  db_dir writable: {_writable(db_path.parent)}")

    output_dir = REPO_ROOT / bundle.outputs["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"  output_dir:      {output_dir.relative_to(REPO_ROOT)}")
    print(f"  out dir writable:{_writable(output_dir)}")
    print()

    # 3. Initialise schema
    print("[3/4] Initialising SQLite schema (idempotent)...")
    crm = build_crm_adapter({**bundle.crm, "db_path": str(db_path)})
    health = await crm.health_check()
    if not health.get("ok"):
        _fail(f"sqlite health check failed: {health}")
        return 2
    print(f"  health:          OK")
    print(f"  current targets: {health.get('target_count', 0)}")
    print()

    # 4. Summary
    print("[4/4] Pre-flight summary")
    print(f"  customer dir:    customers/powerplay/")
    print(f"  vertical pack:   verticals/{bundle.vertical}/")
    print(f"  enabled agents:  {sum(1 for t in bundle.agents.values() if t.enabled)}")
    print(f"  pipeline.db:     {db_path}")
    print(f"  deliverables:    {output_dir}")
    print()
    print("Bootstrap successful. Safe to import the Paperclip company")
    print("definition (ops/paperclip_company_template.yaml) and wake")
    print("agents one at a time, starting with target_identifier.")
    return 0


def _writable(p: Path) -> str:
    test = p / ".write_probe"
    try:
        test.write_text("x")
        test.unlink()
        return "yes"
    except OSError:
        return "no"


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    sys.exit(main())
