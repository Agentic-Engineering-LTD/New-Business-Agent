"""CRM adapter interface and implementations."""

from nba_platform.integrations.crm.base import (
    CrmAdapter,
    CrmConfigError,
    PendingApproval,
    RecordKind,
    RecordRef,
    SearchHit,
    UpsertResult,
    build_crm_adapter,
)

__all__ = [
    "CrmAdapter",
    "CrmConfigError",
    "PendingApproval",
    "RecordKind",
    "RecordRef",
    "SearchHit",
    "UpsertResult",
    "build_crm_adapter",
]
