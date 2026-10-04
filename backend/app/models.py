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
from .comm.models import Conversation, Message
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
    ProductVariant,
    ReorderAlert,
    Shortage,
    StockBalance,
    SupplierOffer,
    TransferOrder,
    TransferOrderLine,
)
from .logistics.models import (
    DeliveryShortage,
    DeliverySlot,
    Shipment,
    ShipmentLeg,
)
from .partners.models import (
    PartnerAccrual,
    PartnerDeposit,
    PartnerTerms,
)
from .pos.models import (
    PosBatch,
    PosSale,
    PosSaleLine,
)
from .production.models import (
    ManufacturingOrder,
    MOMaterial,
    MOStage,
)
from .sales.models import (
    CreditOverride,
    CreditTierSetting,
    CustomerCreditTier,
    CustomerDue,
    EscalationEvent,
    PaymentApproval,
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
    "Conversation",
    "CreditOverride",
    "CreditTierSetting",
    "CustomerCreditTier",
    "CustomerDue",
    "CustomerProfile",
    "DeferredTerm",
    "DeliveryShortage",
    "DeliverySlot",
    "EscalationEvent",
    "EventJournalMap",
    "ImpersonationGrant",
    "JournalEntry",
    "JournalLine",
    "MOMaterial",
    "MOStage",
    "ManufacturingOrder",
    "Message",
    "Order",
    "OrderLine",
    "OrderSubOrder",
    "OtpRequest",
    "PartnerAccrual",
    "PartnerDeposit",
    "PartnerTerms",
    "PaymentApproval",
    "Period",
    "Permission",
    "PosBatch",
    "PosSale",
    "PosSaleLine",
    "PriceLock",
    "Product",
    "ProductVariant",
    "ReorderAlert",
    "Rfq",
    "RfqOffer",
    "Role",
    "RolePermission",
    "Session",
    "Shipment",
    "ShipmentLeg",
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
