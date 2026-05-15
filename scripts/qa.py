"""Repo-wide QA — validates the discipline the platform commits to.

Run from the repo root::

    python scripts/qa.py

Or, after ``pip install -e .``::

    nba-qa

Exits 0 if every check passes, 1 otherwise. Designed to be run in CI and
locally before any commit to ``platform/`` or ``verticals/``.

Checks performed:

  1. Required top-level files present (LICENSE, README, pyproject.toml).
  2. LICENSE is MIT with the correct copyright holder.
  3. No ``.env`` files committed.
  4. No vertical-specific terms have leaked into ``platform/``.
  5. No customer names have leaked into ``platform/`` or ``verticals/``.
  6. Every agent directory under ``platform/agents/`` has a SKILL.md.
  7. Every adapter area in ``platform/integrations/`` has ``base.py`` and
     at least one concrete implementation.
  8. Every customer config directory has the eight required YAML files
     plus README.md.
  9. Every populated vertical pack has ``schemas/``, ``data_sources/``,
     ``ranking/``, ``outputs/`` populated; placeholder packs are detected
     and excused.
 10. Every customer's config loads cleanly through the loader.
 11. Pydantic models import without raising.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Terms that suggest a vertical-specific concept has leaked into the
# platform layer. Add to this list when adding a new vertical pack.
VERTICAL_LEAK_TERMS = (
    "recruitment", "recruiter", "candidate", "hiring manager", "talent acquisition",
    "supermarket", "buying director", "category manager", "senior buyer",
    "retailer", "retail trading", "licensing manager", "private label",
    "brand_licensing", "licensed apparel", "kidswear", "apparel",
)

# Customer keys that must not appear anywhere outside their own directory.
CUSTOMER_KEYS = ("powerplay",)


class QaReport:
    def __init__(self) -> None:
        self.checks: list[tuple[str, bool, str]] = []

    def record(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append((name, ok, detail))

    @property
    def passed(self) -> bool:
        return all(ok for _, ok, _ in self.checks)

    def print_report(self) -> None:
        width = max(len(name) for name, _, _ in self.checks) + 2
        print("\nQA REPORT")
        print("=" * (width + 12))
        for name, ok, detail in self.checks:
            status = "PASS" if ok else "FAIL"
            print(f"  [{status}] {name.ljust(width)} {detail}")
        print("=" * (width + 12))
        if self.passed:
            print("All checks passed.\n")
        else:
            failed = sum(1 for _, ok, _ in self.checks if not ok)
            print(f"{failed} check(s) failed.\n")


# ----------------------------------------------------------------------
# Individual checks
# ----------------------------------------------------------------------


def check_top_level_files(report: QaReport) -> None:
    required = ("README.md", "LICENSE", "pyproject.toml", ".gitignore")
    missing = [f for f in required if not (REPO_ROOT / f).exists()]
    report.record(
        "Top-level files present",
        not missing,
        "missing: " + ", ".join(missing) if missing else "",
    )


def check_license(report: QaReport) -> None:
    license_path = REPO_ROOT / "LICENSE"
    if not license_path.exists():
        report.record("LICENSE is MIT with correct holder", False, "LICENSE missing")
        return
    text = license_path.read_text(encoding="utf-8")
    is_mit = "MIT License" in text or "Permission is hereby granted, free of charge" in text
    has_holder = "Agentic Engineering" in text
    ok = is_mit and has_holder
    detail = ""
    if not is_mit:
        detail = "not recognised as MIT"
    elif not has_holder:
        detail = "Agentic Engineering not named as copyright holder"
    report.record("LICENSE is MIT with correct holder", ok, detail)


def check_no_env_files(report: QaReport) -> None:
    env_files = [p for p in REPO_ROOT.rglob(".env") if p.is_file()]
    report.record(
        "No .env files committed",
        not env_files,
        "found: " + ", ".join(str(p.relative_to(REPO_ROOT)) for p in env_files) if env_files else "",
    )


def _iter_text_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        if "__pycache__" in path.parts:
            continue
        if path.suffix in {".py", ".md", ".yaml", ".yml", ".toml"}:
            out.append(path)
    return out


def check_no_vertical_leak_in_platform(report: QaReport) -> None:
    platform_dir = REPO_ROOT / "nba_platform"
    offenders: list[tuple[Path, str, int]] = []
    for path in _iter_text_files(platform_dir):
        # The Python ``platform`` module collides with our original package
        # name — that's why the package is ``nba_platform``. Check on a
        # per-line basis to allow nuanced exclusions.
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for term in VERTICAL_LEAK_TERMS:
            # Word-boundary match to avoid false positives on substrings.
            pattern = r"\b" + re.escape(term.lower()) + r"\b"
            for match in re.finditer(pattern, text):
                line_no = text.count("\n", 0, match.start()) + 1
                offenders.append((path, term, line_no))
    if offenders:
        details = "; ".join(
            f"{p.relative_to(REPO_ROOT)}:{ln} '{t}'" for p, t, ln in offenders[:5]
        )
        if len(offenders) > 5:
            details += f" (+{len(offenders) - 5} more)"
        report.record("No vertical leak in platform/", False, details)
    else:
        report.record("No vertical leak in platform/", True)


def check_no_customer_leak_outside_customer_dir(report: QaReport) -> None:
    offenders: list[tuple[Path, str]] = []
    for customer in CUSTOMER_KEYS:
        pattern = re.compile(r"\b" + re.escape(customer) + r"\b", re.IGNORECASE)
        for path in _iter_text_files(REPO_ROOT):
            rel = path.relative_to(REPO_ROOT)
            parts = rel.parts
            # Skip the customer's own directory
            if len(parts) >= 2 and parts[0] == "customers" and parts[1].lower() == customer:
                continue
            # Skip ops/, docs/, scripts/, tests/, README — those are legitimate
            # references to the first customer for documentation purposes.
            if parts[0] in {"ops", "docs", "scripts", "tests"}:
                continue
            if rel.as_posix() == "README.md":
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if pattern.search(text):
                offenders.append((path, customer))
    if offenders:
        details = "; ".join(
            f"{p.relative_to(REPO_ROOT)} mentions {c!r}" for p, c in offenders[:5]
        )
        if len(offenders) > 5:
            details += f" (+{len(offenders) - 5} more)"
        report.record("No customer leak outside customers/", False, details)
    else:
        report.record("No customer leak outside customers/", True)


def check_every_agent_has_skill_md(report: QaReport) -> None:
    expected_agents = (
        "target_identifier",
        "org_mapper",
        "contact_enricher",
        "opportunity_assessor",
        "hand_off",
        "refresh_watch",
        "outreach_drafter",
        "proactive_recommender",
    )
    missing: list[str] = []
    agents_dir = REPO_ROOT / "nba_platform" / "agents"
    for name in expected_agents:
        skill = agents_dir / name / "SKILL.md"
        if not skill.exists():
            missing.append(name)
    report.record(
        "Every agent has SKILL.md",
        not missing,
        "missing: " + ", ".join(missing) if missing else "",
    )


def check_adapter_areas(report: QaReport) -> None:
    integrations_dir = REPO_ROOT / "nba_platform" / "integrations"
    expected_areas = ("crm", "llm", "enrichment", "search")
    issues: list[str] = []
    for area in expected_areas:
        area_dir = integrations_dir / area
        if not (area_dir / "base.py").exists():
            issues.append(f"{area}: missing base.py")
            continue
        impls = [p for p in area_dir.glob("*.py") if p.name not in ("__init__.py", "base.py")]
        if not impls:
            issues.append(f"{area}: no concrete implementation")
    report.record(
        "Every adapter has base + ≥1 impl",
        not issues,
        "; ".join(issues),
    )


def check_customer_dirs(report: QaReport) -> None:
    required_files = (
        "company.yaml",
        "targets.yaml",
        "brand.yaml",
        "personas.yaml",
        "thresholds.yaml",
        "crm.yaml",
        "enrichment.yaml",
        "outputs.yaml",
        "agents.yaml",
        "README.md",
    )
    issues: list[str] = []
    customers_root = REPO_ROOT / "customers"
    for customer_dir in sorted(customers_root.iterdir()):
        if not customer_dir.is_dir() or customer_dir.name.startswith("."):
            continue
        for filename in required_files:
            if not (customer_dir / filename).exists():
                issues.append(f"{customer_dir.name}/{filename}")
    report.record(
        "Every customer has required files",
        not issues,
        "missing: " + ", ".join(issues) if issues else "",
    )


def check_vertical_packs(report: QaReport) -> None:
    """Populated packs need all four sections; placeholders are excused."""
    required_sections = ("schemas", "data_sources", "ranking", "outputs")
    issues: list[str] = []
    verticals_root = REPO_ROOT / "verticals"
    for pack_dir in sorted(verticals_root.iterdir()):
        if not pack_dir.is_dir() or pack_dir.name.startswith("."):
            continue
        readme = pack_dir / "README.md"
        if readme.exists():
            text = readme.read_text(encoding="utf-8", errors="ignore").lower()
            if "placeholder" in text or "not populated" in text:
                # Placeholder pack — only the README is required, and the
                # config loader will reject any customer pinned to it.
                continue
        for section in required_sections:
            section_dir = pack_dir / section
            if not section_dir.is_dir():
                issues.append(f"{pack_dir.name}/{section}/ missing")
                continue
            populated = list(section_dir.glob("*"))
            if not populated:
                issues.append(f"{pack_dir.name}/{section}/ empty")
    report.record(
        "Vertical packs structurally complete",
        not issues,
        "; ".join(issues),
    )


def check_customer_configs_load(report: QaReport) -> None:
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from nba_platform.lib.config_loader import load_customer_bundle  # noqa: WPS433
    except Exception as e:  # noqa: BLE001
        report.record("Config loader importable", False, str(e))
        return
    report.record("Config loader importable", True)

    customers_root = REPO_ROOT / "customers"
    failures: list[str] = []
    for customer_dir in sorted(customers_root.iterdir()):
        if not customer_dir.is_dir() or customer_dir.name.startswith("."):
            continue
        try:
            load_customer_bundle(customer_dir.name)
        except Exception as e:  # noqa: BLE001
            failures.append(f"{customer_dir.name}: {e}")
    report.record(
        "Customer configs load cleanly",
        not failures,
        "; ".join(failures),
    )


def check_pydantic_models_import(report: QaReport) -> None:
    sys.path.insert(0, str(REPO_ROOT))
    issues: list[str] = []
    modules = (
        "nba_platform.integrations.crm.base",
        "nba_platform.integrations.crm.sqlite",
        "nba_platform.integrations.crm.airtable",
        "nba_platform.integrations.crm.stackone",
        "nba_platform.integrations.llm.base",
        "nba_platform.integrations.enrichment.base",
        "nba_platform.integrations.enrichment.router",
        "nba_platform.integrations.enrichment.cognism",
        "nba_platform.integrations.enrichment.apollo",
        "nba_platform.integrations.enrichment.hunter",
        "nba_platform.integrations.enrichment.lusha",
        "nba_platform.integrations.search.base",
        "nba_platform.governance.audit",
        "nba_platform.governance.budget",
        "nba_platform.governance.approval",
        "nba_platform.evals.metrics",
        "nba_platform.evals.harness",
        "nba_platform.outputs.base",
        "nba_platform.outputs.xlsx_exporter",
        "nba_platform.lib.config_loader",
    )
    for mod_name in modules:
        try:
            __import__(mod_name)
        except Exception as e:  # noqa: BLE001
            issues.append(f"{mod_name}: {e}")
    report.record(
        "Platform modules import cleanly",
        not issues,
        "; ".join(issues),
    )


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------


def main() -> int:
    report = QaReport()
    check_top_level_files(report)
    check_license(report)
    check_no_env_files(report)
    check_no_vertical_leak_in_platform(report)
    check_no_customer_leak_outside_customer_dir(report)
    check_every_agent_has_skill_md(report)
    check_adapter_areas(report)
    check_customer_dirs(report)
    check_vertical_packs(report)
    check_customer_configs_load(report)
    check_pydantic_models_import(report)
    report.print_report()
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
