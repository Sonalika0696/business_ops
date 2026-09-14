"""Shared enums used across the data model.

These mirror DESIGN.md §2 (entity columns) and §3 (canonical settlement
line-item contract) exactly. Do not add/remove/rename values without going
through the contract-freeze process described in DESIGN.md's header.
"""

import enum


class MsmeClassification(enum.StrEnum):
    """Seller.msme_classification — DESIGN.md §2.1."""

    MICRO = "MICRO"
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    NONE = "NONE"


class MarketplaceCode(enum.StrEnum):
    """Marketplace.code — DESIGN.md §2.2."""

    AMAZON_IN = "AMAZON_IN"
    FLIPKART = "FLIPKART"
    MEESHO = "MEESHO"


class FulfillmentType(enum.StrEnum):
    """SellerMarketplaceAccount.fulfillment_type — DESIGN.md §2.3."""

    SELF_SHIP = "SELF_SHIP"
    FBA = "FBA"
    FLIPKART_ADVANTAGE = "FLIPKART_ADVANTAGE"
    MEESHO_SUPPLIER = "MEESHO_SUPPLIER"


class GstRate(int, enum.Enum):
    """Product.gst_rate / OrderLineItem.unit_gst_rate — DESIGN.md §2.4/§2.7.

    Int-valued so the stored value is the actual GST percentage.
    """

    ZERO = 0
    FIVE = 5
    TWELVE = 12
    EIGHTEEN = 18
    TWENTY_EIGHT = 28


class OrderStatus(enum.StrEnum):
    """Order.order_status — DESIGN.md §2.6."""

    PLACED = "PLACED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RETURNED = "RETURNED"
    RTO = "RTO"


class PaymentType(enum.StrEnum):
    """Order.payment_type — DESIGN.md §2.6."""

    PREPAID = "PREPAID"
    COD = "COD"


class ShippingZone(enum.StrEnum):
    """Order.shipping_zone — DESIGN.md §2.6."""

    LOCAL = "LOCAL"
    REGIONAL = "REGIONAL"
    NATIONAL = "NATIONAL"


class ListingStatus(enum.StrEnum):
    """SKUMarketplaceListing.listing_status — DESIGN.md §2.5."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUPPRESSED = "SUPPRESSED"


class SettlementStatus(enum.StrEnum):
    """SettlementReport.status — DESIGN.md §2.8 / §4 (job-lifecycle contract)."""

    UPLOADED = "UPLOADED"
    PARSING = "PARSING"
    PARSED = "PARSED"
    RECONCILING = "RECONCILING"
    RECONCILED = "RECONCILED"
    FAILED = "FAILED"


class AmountCanonical(enum.StrEnum):
    """SettlementLineItem.amount_canonical — DESIGN.md §3 (frozen, exactly 14 values).

    Sign convention (enforced by application logic, not the DB):
    fee/deduction types are stored negative; credit types keep their
    natural sign (ADJUSTMENT can be either).
    """

    REFERRAL_FEE = "REFERRAL_FEE"
    CLOSING_FEE = "CLOSING_FEE"
    SHIPPING_FEE = "SHIPPING_FEE"
    COLLECTION_FEE = "COLLECTION_FEE"
    FBA_FEE = "FBA_FEE"
    STORAGE_FEE = "STORAGE_FEE"
    ADVERTISING_FEE = "ADVERTISING_FEE"
    PROMOTION_REBATE = "PROMOTION_REBATE"
    TCS = "TCS"
    TDS = "TDS"
    REFUND = "REFUND"
    REIMBURSEMENT = "REIMBURSEMENT"
    ADJUSTMENT = "ADJUSTMENT"
    GST_ON_FEE = "GST_ON_FEE"


class MatchStatus(enum.StrEnum):
    """SettlementLineItem.match_status — DESIGN.md §2.9.

    Phase 1 only ever produces MATCHED_EXACT / UNMATCHED / ADJUSTMENT;
    MATCHED_FUZZY is defined-but-unused until Phase 2 (DESIGN.md §8).
    """

    UNMATCHED = "UNMATCHED"
    MATCHED_EXACT = "MATCHED_EXACT"
    MATCHED_FUZZY = "MATCHED_FUZZY"
    ADJUSTMENT = "ADJUSTMENT"


class FeeType(enum.StrEnum):
    """FeeSchedule.fee_type — DESIGN.md §2.10."""

    REFERRAL = "REFERRAL"
    CLOSING = "CLOSING"
    SHIPPING = "SHIPPING"
    FBA = "FBA"
    COLLECTION = "COLLECTION"


class ReturnReason(enum.StrEnum):
    """Return.return_reason — DESIGN.md §2.11."""

    DAMAGED = "DAMAGED"
    WRONG_ITEM = "WRONG_ITEM"
    NOT_AS_DESCRIBED = "NOT_AS_DESCRIBED"
    CHANGE_OF_MIND = "CHANGE_OF_MIND"
    DEFECTIVE = "DEFECTIVE"
    RTO_UNDELIVERED = "RTO_UNDELIVERED"


class ReturnType(enum.StrEnum):
    """Return.return_type — DESIGN.md §2.11."""

    CUSTOMER_RETURN = "CUSTOMER_RETURN"
    RTO = "RTO"


class ReturnStatus(enum.StrEnum):
    """Return.return_status — DESIGN.md §2.11."""

    INITIATED = "INITIATED"
    IN_TRANSIT = "IN_TRANSIT"
    RECEIVED = "RECEIVED"
    INSPECTED = "INSPECTED"
    REFUNDED = "REFUNDED"
    REIMBURSED = "REIMBURSED"
    DISPUTED = "DISPUTED"


class InventoryDisposition(enum.StrEnum):
    """Return.inventory_disposition — DESIGN.md §2.11."""

    RESTOCKED = "RESTOCKED"
    DAMAGED = "DAMAGED"
    LOST = "LOST"
    DISPOSED = "DISPOSED"
    NOT_YET_RETURNED = "NOT_YET_RETURNED"


class ClaimStatus(enum.StrEnum):
    """Return.claim_status — DESIGN.md §2.11."""

    NOT_CLAIMED = "NOT_CLAIMED"
    CLAIMED = "CLAIMED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
