"""Configuration loader.

Reads a customer's deployment configuration as the union of:

  customers/<customer>/*.yaml          # customer config
  verticals/<vertical>/**.yaml         # vertical pack
  (no platform-level YAML — platform behaviour is in code)

Produces a validated ``ConfigBundle`` that agents consume. Validation rejects
the deployment if the customer config references a vertical pack the customer
isn't pinned to, or if any required file is missing.

This module is the single entry point for "what configuration applies to this
customer?" — anything that wants to know reads from a ConfigBundle.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[2]


class ConfigError(Exception):
    pass


class AgentToggle(BaseModel):
    enabled: bool
    notes: str | None = None


class CustomerMeta(BaseModel):
    """Loaded from ``customers/<customer>/company.yaml`` (top-level keys)."""

    name: str
    vertical: str
    timezone: str = "Europe/London"


class ConfigBundle(BaseModel):
    """The merged, validated config for one customer deployment."""

    customer: str
    vertical: str
    meta: CustomerMeta
    targets: dict[str, Any]
    brand: dict[str, Any]
    personas: dict[str, Any]
    thresholds: dict[str, Any]
    crm: dict[str, Any]
    enrichment: dict[str, Any]
    outputs: dict[str, Any]
    agents: dict[str, AgentToggle]
    vertical_pack: dict[str, Any] = Field(default_factory=dict)

    @property
    def vertical_root(self) -> Path:
        return REPO_ROOT / "verticals" / self.vertical


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"required config file not found: {path.relative_to(REPO_ROOT)}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a YAML mapping at top level")
    return data


def load_customer_bundle(customer: str) -> ConfigBundle:
    """Load and validate the full config bundle for ``customer``.

    Raises ``ConfigError`` on any missing or malformed input. Never returns
    a partially-valid bundle.
    """
    customer_dir = REPO_ROOT / "customers" / customer
    if not customer_dir.is_dir():
        raise ConfigError(f"no customer directory at {customer_dir.relative_to(REPO_ROOT)}")

    company = _load_yaml(customer_dir / "company.yaml")
    meta = CustomerMeta(**company)

    vertical_dir = REPO_ROOT / "verticals" / meta.vertical
    if not vertical_dir.is_dir():
        raise ConfigError(
            f"customer {customer!r} is pinned to vertical {meta.vertical!r} "
            f"but no vertical pack exists at {vertical_dir.relative_to(REPO_ROOT)}"
        )

    targets = _load_yaml(customer_dir / "targets.yaml")
    brand = _load_yaml(customer_dir / "brand.yaml")
    personas = _load_yaml(customer_dir / "personas.yaml")
    thresholds = _load_yaml(customer_dir / "thresholds.yaml")
    crm = _load_yaml(customer_dir / "crm.yaml")
    enrichment = _load_yaml(customer_dir / "enrichment.yaml")
    outputs = _load_yaml(customer_dir / "outputs.yaml")
    agents_raw = _load_yaml(customer_dir / "agents.yaml")

    agents: dict[str, AgentToggle] = {}
    for agent_name, cfg in agents_raw.items():
        if isinstance(cfg, bool):
            agents[agent_name] = AgentToggle(enabled=cfg)
        elif isinstance(cfg, dict):
            agents[agent_name] = AgentToggle(**cfg)
        else:
            raise ConfigError(
                f"agents.yaml entry for {agent_name!r} must be a bool or mapping"
            )

    # Vertical pack — load schemas, ranking config, output template metadata
    vertical_pack = _load_vertical_pack(vertical_dir)

    return ConfigBundle(
        customer=customer,
        vertical=meta.vertical,
        meta=meta,
        targets=targets,
        brand=brand,
        personas=personas,
        thresholds=thresholds,
        crm=crm,
        enrichment=enrichment,
        outputs=outputs,
        agents=agents,
        vertical_pack=vertical_pack,
    )


def _load_vertical_pack(vertical_dir: Path) -> dict[str, Any]:
    """Walk the vertical pack and load its YAML inputs into a single dict.

    Structure (every vertical pack must follow this):
      schemas/*.yaml          field definitions per RecordKind
      data_sources/*.yaml     enrichment + signal sources
      ranking/*.yaml          scoring weights and rules
    """
    pack: dict[str, dict[str, Any]] = {"schemas": {}, "data_sources": {}, "ranking": {}}

    for section in pack:
        section_dir = vertical_dir / section
        if not section_dir.is_dir():
            continue
        for yaml_file in sorted(section_dir.glob("*.yaml")):
            key = yaml_file.stem
            pack[section][key] = _load_yaml(yaml_file)

    return pack
