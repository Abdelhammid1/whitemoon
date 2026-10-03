"""Aggregator — importing this module registers every model on `Base.metadata`.

Alembic's env.py imports from here so autogenerate / upgrade sees the full
schema. Each domain owns its own `models.py`; this file only re-exports.
"""

from __future__ import annotations

from .accounting.models import (
    Account,
    BankReceipt,
    DeferredTerm,
    EventJournalMap,
    JournalEntry,
    JournalLine,
    Period,
)
from .audit.models import AuditEvent
from .inventory.models import (
    Batch,
    Product,
    ReorderAlert,
    Shortage,
    StockBalance,
    SupplierOffer,
    TransferOrder,
    TransferOrderLine,
)
from .identity.models import (
    BackupCode,
    ChannelPartnerProfile,
    CustomerProfile,
    ImpersonationGrant,
    OtpRequest,
    Permission,
    Role,
    RolePermission,
    Session,
    SupplierProfile,
    TotpSecret,
    User,
    UserRole,
)

__all__ = [
    "Account",
    "AuditEvent",
    "BackupCode",
    "BankReceipt",
    "Batch",
    "ChannelPartnerProfile",
    "CustomerProfile",
    "DeferredTerm",
    "EventJournalMap",
    "ImpersonationGrant",
    "JournalEntry",
    "JournalLine",
    "OtpRequest",
    "Period",
    "Permission",
    "Product",
    "ReorderAlert",
    "Role",
    "RolePermission",
    "Session",
    "Shortage",
    "StockBalance",
    "SupplierOffer",
    "SupplierProfile",
    "TotpSecret",
    "TransferOrder",
    "TransferOrderLine",
    "User",
    "UserRole",
]
