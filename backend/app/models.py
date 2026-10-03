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
from .commerce.models import (
    Cart,
    CartItem,
    Order,
    OrderLine,
    OrderSubOrder,
    PriceLock,
    Rfq,
    RfqOffer,
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
from .partners.models import (
    PartnerAccrual,
    PartnerDeposit,
    PartnerTerms,
)
from .production.models import (
    ManufacturingOrder,
    MOMaterial,
    MOStage,
)
from .sales.models import (
    CreditOverride,
    CustomerCreditTier,
    CustomerDue,
    EscalationEvent,
)

__all__ = [
    "Account",
    "AuditEvent",
    "BackupCode",
    "BankReceipt",
    "Batch",
    "Cart",
    "CartItem",
    "ChannelPartnerProfile",
    "CreditOverride",
    "CustomerCreditTier",
    "CustomerDue",
    "CustomerProfile",
    "DeferredTerm",
    "EscalationEvent",
    "EventJournalMap",
    "ImpersonationGrant",
    "JournalEntry",
    "JournalLine",
    "MOMaterial",
    "MOStage",
    "ManufacturingOrder",
    "Order",
    "OrderLine",
    "OrderSubOrder",
    "OtpRequest",
    "PartnerAccrual",
    "PartnerDeposit",
    "PartnerTerms",
    "Period",
    "Permission",
    "PriceLock",
    "Product",
    "ReorderAlert",
    "Rfq",
    "RfqOffer",
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
