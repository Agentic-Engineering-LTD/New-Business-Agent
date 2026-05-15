"""Contract test for CRM adapter implementations.

Verifies every concrete ``CrmAdapter`` subclass implements the abstract
interface — not by instantiating them, but by introspecting the class so
the test doesn't require live credentials.
"""

from __future__ import annotations

import inspect

from nba_platform.integrations.crm.airtable import AirtableAdapter
from nba_platform.integrations.crm.base import CrmAdapter
from nba_platform.integrations.crm.sqlite import SqliteAdapter
from nba_platform.integrations.crm.stackone import StackOneAdapter

REQUIRED_METHODS = (
    "upsert",
    "attach_note",
    "search",
    "list_pending_approvals",
    "resolve_approval",
    "health_check",
)

ADAPTERS = (SqliteAdapter, AirtableAdapter, StackOneAdapter)


def test_adapters_are_subclasses_of_base() -> None:
    for adapter_cls in ADAPTERS:
        assert issubclass(adapter_cls, CrmAdapter), (
            f"{adapter_cls.__name__} must subclass CrmAdapter"
        )


def test_adapters_implement_required_methods() -> None:
    for adapter_cls in ADAPTERS:
        for method_name in REQUIRED_METHODS:
            assert hasattr(adapter_cls, method_name), (
                f"{adapter_cls.__name__} missing method {method_name!r}"
            )
            method = getattr(adapter_cls, method_name)
            assert callable(method)


def test_adapter_method_signatures_match_base() -> None:
    """Concrete adapters must keep the base class's signatures intact."""
    for adapter_cls in ADAPTERS:
        for method_name in REQUIRED_METHODS:
            base_method = getattr(CrmAdapter, method_name)
            concrete_method = getattr(adapter_cls, method_name)
            base_sig = inspect.signature(base_method)
            concrete_sig = inspect.signature(concrete_method)
            # Compare parameter names, not annotations — annotations may be
            # narrowed in a subclass.
            assert list(base_sig.parameters) == list(concrete_sig.parameters), (
                f"{adapter_cls.__name__}.{method_name} signature drifted from base"
            )
