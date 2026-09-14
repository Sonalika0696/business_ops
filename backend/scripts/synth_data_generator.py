"""Phase 1/2 synthetic data generator — DESIGN.md §5 + §11.5.

Standalone script, not part of the running app. Deterministic given
`--seed` (default fixed value, for reproducible CI/demo runs): seeds one
`Seller`, 15 `Product`s (shared across marketplaces, DESIGN.md §2.4), and
one `SellerMarketplaceAccount` per marketplace (Amazon, Flipkart, Meesho) —
each with its own 1:1 `SKUMarketplaceListing`s and its own 50 `Order`s + one
`OrderLineItem` each (orders are scoped to one account, so each marketplace
gets its own order set, DESIGN.md §11.5), and emits that marketplace's own
settlement fixture + ground-truth summary:
  - `tests/fixtures/amazon_settlement_sample.txt` (§8 shape) /
    `amazon_settlement_sample.ground_truth.json`
  - `tests/fixtures/flipkart_settlement_sample.csv` (§11.2 shape) /
    `flipkart_settlement_sample.ground_truth.json`
  - `tests/fixtures/meesho_settlement_sample.csv` (§11.2 shape, UTF-8 BOM) /
    `meesho_settlement_sample.ground_truth.json`
all consumed by `scripts/demo_e2e.py`.

Idempotency note (a deviation from a literal reading of "standalone script"):
re-running this script is meant to be safe for a repeated demo, so if a
`Seller` with the fixed demo email already exists, all of its previously
generated rows (products, listings, orders + line items, and any settlement
reports/line items against ANY of its marketplace accounts) are wiped first,
then regenerated fresh from the given seed. This keeps the *content*
deterministic per seed without accumulating duplicate rows / unique-
constraint failures across runs. `_wipe_existing_demo_data` already queries
by `seller_id` (not filtered to one marketplace), so it covers all 3
accounts without needing marketplace-specific changes.

Usage:
    uv run python scripts/synth_data_generator.py [--seed 42]
"""

import argparse
import json
import random
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

# Allow running as `python scripts/synth_data_generator.py` (not just
# `python -m scripts.synth_data_generator`) — see scripts/seed_reference_data.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

# Side-effect import: registers all 12 model classes onto the shared
# declarative registry before this script's first query. This script is a
# standalone entry point (never imports app.main) and only imports the
# specific model classes it directly constructs below — without this,
# SQLAlchemy's lazy mapper configuration can fail to resolve a
# relationship() string against a class this script never itself imports
# (e.g. Marketplace -> FeeSchedule/Return).
import app.all_models  # noqa: E402, F401
from app.core.db_sync import get_sync_session  # noqa: E402
from app.core.enums import (  # noqa: E402
    FulfillmentType,
    ListingStatus,
    MarketplaceCode,
    OrderStatus,
    PaymentType,
    ShippingZone,
)
from app.core.security import hash_password  # noqa: E402
from app.modules.ingestion.models import SettlementLineItem, SettlementReport  # noqa: E402
from app.modules.masters.models import Marketplace, Product, SellerMarketplaceAccount  # noqa: E402
from app.modules.pricing.models import SKUMarketplaceListing  # noqa: E402
from app.modules.reconciliation.models import Order, OrderLineItem  # noqa: E402
from app.modules.sellers.models import Seller  # noqa: E402

DEMO_SELLER_EMAIL = "demo@seller.test"
DEFAULT_SEED = 42
N_PRODUCTS = 15
M_ORDERS = 50
ORDERS_WITHOUT_LINES = 5
ORDERS_WITH_LINES = M_ORDERS - ORDERS_WITHOUT_LINES  # 45, per DESIGN.md §5 step 3
PERIOD_START = date(2026, 8, 1)
PERIOD_DAYS = 30

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
SETTLEMENT_FIXTURE_PATH = FIXTURES_DIR / "amazon_settlement_sample.txt"
GROUND_TRUTH_PATH = FIXTURES_DIR / "amazon_settlement_sample.ground_truth.json"

# DESIGN.md §11.5 — Flipkart/Meesho fixtures, each with its own 50-order set
# scoped to its own SellerMarketplaceAccount (orders cannot share Amazon's,
# since Order is scoped to one account). Same ~45/5 matched/unmatched split
# and 3-4 orphan lines as the Amazon fixture (DESIGN.md §5 step 3).
FLIPKART_SETTLEMENT_FIXTURE_PATH = FIXTURES_DIR / "flipkart_settlement_sample.csv"
FLIPKART_GROUND_TRUTH_PATH = FIXTURES_DIR / "flipkart_settlement_sample.ground_truth.json"
MEESHO_SETTLEMENT_FIXTURE_PATH = FIXTURES_DIR / "meesho_settlement_sample.csv"
MEESHO_GROUND_TRUTH_PATH = FIXTURES_DIR / "meesho_settlement_sample.ground_truth.json"

# 15 (category_primary, category_sub, gst_rate) triples — spans all 5 legal
# GST rates (DESIGN.md §2.4) across a few plausible categories.
CATEGORIES: list[tuple[str, str, int]] = [
    ("Apparel", "Apparel/Shirts", 5),
    ("Apparel", "Apparel/Trousers", 12),
    ("Electronics", "Electronics/Accessories", 18),
    ("Electronics", "Electronics/Audio", 18),
    ("Electronics", "Electronics/Mobiles", 18),
    ("Home & Kitchen", "Home/Cookware", 12),
    ("Home & Kitchen", "Home/Storage", 18),
    ("Books", "Books/Fiction", 0),
    ("Grocery", "Grocery/Staples", 5),
    ("Beauty", "Beauty/Skincare", 18),
    ("Toys", "Toys/Educational", 12),
    ("Stationery", "Stationery/Office", 5),
    ("Sports", "Sports/Fitness", 18),
    ("Footwear", "Footwear/Casual", 5),
    ("Furniture", "Furniture/Small", 28),
]
assert len(CATEGORIES) == N_PRODUCTS

INDIAN_STATES = [
    "Maharashtra",
    "Karnataka",
    "Delhi",
    "Tamil Nadu",
    "Gujarat",
    "Uttar Pradesh",
    "West Bengal",
    "Telangana",
]

# Amount-description pool — exact strings from seed_data/amazon_amount_mapping.csv
# (DESIGN.md §8's frozen mapping table), each: (sign, (pct_low, pct_high) of the
# order's gross amount). "sign" mirrors the CSV's `sign_hint` column.
_FeeInfo = tuple[str, tuple[float, float]]
FEE_DESCRIPTIONS: dict[str, _FeeInfo] = {
    "Referral fee": ("negative", (0.08, 0.15)),
    "Variable closing fee": ("negative", (0.02, 0.05)),
    "Fixed closing fee": ("negative", (0.01, 0.03)),
    "Shipping fee": ("negative", (0.03, 0.08)),
    "TCS-IGST": ("negative", (0.01, 0.01)),
    "TDS Section 194-O": ("negative", (0.001, 0.001)),
    "CGST on selling fees": ("negative", (0.008, 0.015)),
    "Sponsored Products charge": ("negative", (0.01, 0.04)),
    "Monthly storage fee": ("negative", (0.005, 0.02)),
    "Promotional rebate": ("positive", (0.01, 0.03)),
    "FBA inventory reimbursement": ("positive", (0.01, 0.03)),
}
# The first 3 are on every settled order; the rest are sampled to fill out
# DESIGN.md §5's "3-6 fee/tax lines" per order.
CORE_DESCRIPTIONS = ["Referral fee", "Variable closing fee", "Shipping fee"]
EXTRA_DESCRIPTIONS = [d for d in FEE_DESCRIPTIONS if d not in CORE_DESCRIPTIONS]

TRANSACTION_TYPE_BY_DESCRIPTION: dict[str, str] = {
    "Referral fee": "Order",
    "Variable closing fee": "Order",
    "Fixed closing fee": "Order",
    "Shipping fee": "Order",
    "TCS-IGST": "Order",
    "TDS Section 194-O": "Order",
    "CGST on selling fees": "Order",
    "Sponsored Products charge": "Service Fee",
    "Monthly storage fee": "FBA Inventory Fee",
    "Promotional rebate": "Order",
    "FBA inventory reimbursement": "FBA Inventory Fee",
    "Adjustment": "Adjustment",
    "Refund": "Refund",
}

ORPHAN_ORDER_ID_TEMPLATE = "AMZ-ORD-ORPHAN-{:02d}"

# ---------------------------------------------------------------------------
# DESIGN.md §11.5 — Flipkart fixture vocabulary (from
# seed_data/flipkart_amount_mapping.csv), same shape as the Amazon pool
# above: 3 core descriptions on every settled order + a sampled pool of
# extras to fill out 3-6 lines/order.
# ---------------------------------------------------------------------------
FLIPKART_FEE_DESCRIPTIONS: dict[str, _FeeInfo] = {
    "Commission": ("negative", (0.08, 0.15)),
    "Fixed fee": ("negative", (0.02, 0.05)),
    "Shipping fee": ("negative", (0.03, 0.08)),
    "Collection fee": ("negative", (0.01, 0.03)),
    "TCS collected": ("negative", (0.01, 0.01)),
    "TDS deducted": ("negative", (0.001, 0.001)),
    "CGST on fees": ("negative", (0.008, 0.015)),
    "Sponsored ads fee": ("negative", (0.01, 0.04)),
    "Storage fee": ("negative", (0.005, 0.02)),
    "Seller promotion reimbursement": ("positive", (0.01, 0.03)),
    "Return premium reimbursement": ("positive", (0.01, 0.03)),
}
FLIPKART_CORE_DESCRIPTIONS = ["Commission", "Fixed fee", "Shipping fee"]
FLIPKART_EXTRA_DESCRIPTIONS = [
    d for d in FLIPKART_FEE_DESCRIPTIONS if d not in FLIPKART_CORE_DESCRIPTIONS
]
FLIPKART_TRANSACTION_TYPE_BY_DESCRIPTION: dict[str, str] = {
    "Commission": "Sale",
    "Fixed fee": "Sale",
    "Shipping fee": "Sale",
    "Collection fee": "Sale",
    "TCS collected": "Sale",
    "TDS deducted": "Sale",
    "CGST on fees": "Sale",
    "Sponsored ads fee": "Marketing",
    "Storage fee": "Fulfilment",
    "Seller promotion reimbursement": "Sale",
    "Return premium reimbursement": "Return",
    "Miscellaneous adjustment": "Adjustment",
    "Customer refund": "Return",
}
FLIPKART_ORPHAN_DESCRIPTIONS = ["Miscellaneous adjustment", "Customer refund"]
FLIPKART_ORPHAN_ORDER_ID_TEMPLATE = "FK-ORD-ORPHAN-{:02d}"

# ---------------------------------------------------------------------------
# DESIGN.md §11.5 — Meesho fixture vocabulary (from
# seed_data/meesho_amount_mapping.csv). Same shape again.
# ---------------------------------------------------------------------------
MEESHO_FEE_DESCRIPTIONS: dict[str, _FeeInfo] = {
    "Commission": ("negative", (0.08, 0.15)),
    "Fixed fee": ("negative", (0.02, 0.05)),
    "Shipping charge": ("negative", (0.03, 0.08)),
    "Reverse pickup charge": ("negative", (0.01, 0.03)),
    "TCS": ("negative", (0.01, 0.01)),
    "TDS": ("negative", (0.001, 0.001)),
    "CGST on charges": ("negative", (0.008, 0.015)),
    "Ads charge": ("negative", (0.01, 0.04)),
    "Warehousing charge": ("negative", (0.005, 0.02)),
    "Discount reimbursement": ("positive", (0.01, 0.03)),
    "Compensation": ("positive", (0.01, 0.03)),
}
MEESHO_CORE_DESCRIPTIONS = ["Commission", "Fixed fee", "Shipping charge"]
MEESHO_EXTRA_DESCRIPTIONS = [
    d for d in MEESHO_FEE_DESCRIPTIONS if d not in MEESHO_CORE_DESCRIPTIONS
]
MEESHO_TRANSACTION_TYPE_BY_DESCRIPTION: dict[str, str] = {
    "Commission": "Order",
    "Fixed fee": "Order",
    "Shipping charge": "Order",
    "Reverse pickup charge": "Return",
    "TCS": "Order",
    "TDS": "Order",
    "CGST on charges": "Order",
    "Ads charge": "Marketing",
    "Warehousing charge": "Fulfilment",
    "Discount reimbursement": "Order",
    "Compensation": "Claim",
    "Other adjustment": "Adjustment",
    "Refund to customer": "Return",
}
MEESHO_ORPHAN_DESCRIPTIONS = ["Other adjustment", "Refund to customer"]
MEESHO_ORPHAN_ORDER_ID_TEMPLATE = "MSH-ORD-ORPHAN-{:02d}"


def _money_str(amount_paise: int) -> str:
    """Signed integer paise -> decimal-rupee string, e.g. -12345 -> '-123.45'."""
    sign = "-" if amount_paise < 0 else ""
    magnitude = abs(amount_paise)
    return f"{sign}{magnitude // 100}.{magnitude % 100:02d}"


def _wipe_existing_demo_data(session: Session) -> None:
    """Delete any previously-generated rows for the fixed demo seller, in FK order."""
    existing_seller = session.execute(
        select(Seller).where(Seller.email == DEMO_SELLER_EMAIL)
    ).scalar_one_or_none()
    if existing_seller is None:
        return

    account_ids = [
        row[0]
        for row in session.execute(
            select(SellerMarketplaceAccount.id).where(
                SellerMarketplaceAccount.seller_id == existing_seller.id
            )
        ).all()
    ]
    if account_ids:
        report_ids = [
            row[0]
            for row in session.execute(
                select(SettlementReport.id).where(
                    SettlementReport.seller_marketplace_account_id.in_(account_ids)
                )
            ).all()
        ]
        if report_ids:
            session.execute(
                delete(SettlementLineItem).where(
                    SettlementLineItem.settlement_report_id.in_(report_ids)
                )
            )
            session.execute(delete(SettlementReport).where(SettlementReport.id.in_(report_ids)))

        order_ids = [
            row[0]
            for row in session.execute(
                select(Order.id).where(Order.seller_marketplace_account_id.in_(account_ids))
            ).all()
        ]
        if order_ids:
            session.execute(delete(OrderLineItem).where(OrderLineItem.order_id.in_(order_ids)))
            session.execute(delete(Order).where(Order.id.in_(order_ids)))

        session.execute(
            delete(SKUMarketplaceListing).where(
                SKUMarketplaceListing.seller_marketplace_account_id.in_(account_ids)
            )
        )
        session.execute(
            delete(SellerMarketplaceAccount).where(SellerMarketplaceAccount.id.in_(account_ids))
        )

    session.execute(delete(Product).where(Product.seller_id == existing_seller.id))
    session.execute(delete(Seller).where(Seller.id == existing_seller.id))
    session.commit()


def _ensure_marketplace(session: Session) -> Marketplace:
    """Fetch the seeded AMAZON_IN row, or create it inline (mirrors
    scripts/seed_reference_data.py's values) if that script hasn't run yet —
    this script must be able to run standalone."""
    marketplace = session.execute(
        select(Marketplace).where(Marketplace.code == MarketplaceCode.AMAZON_IN)
    ).scalar_one_or_none()
    if marketplace is None:
        marketplace = Marketplace(
            id=uuid.uuid4(),
            code=MarketplaceCode.AMAZON_IN,
            display_name="Amazon India",
            settlement_frequency_days=14,
            payout_split_count=1,
            active=True,
        )
        session.add(marketplace)
        session.commit()
        session.refresh(marketplace)
    return marketplace


def _ensure_flipkart_marketplace(session: Session) -> Marketplace:
    """Fetch the seeded FLIPKART row, or create it inline — mirrors
    `_ensure_marketplace` above but for Flipkart (DESIGN.md §2.2: 2 splits/
    7d), kept as its own function rather than parameterizing the Amazon one,
    per DESIGN.md §11.5's "do not refactor the existing Amazon path"."""
    marketplace = session.execute(
        select(Marketplace).where(Marketplace.code == MarketplaceCode.FLIPKART)
    ).scalar_one_or_none()
    if marketplace is None:
        marketplace = Marketplace(
            id=uuid.uuid4(),
            code=MarketplaceCode.FLIPKART,
            display_name="Flipkart",
            settlement_frequency_days=7,
            payout_split_count=2,
            active=True,
        )
        session.add(marketplace)
        session.commit()
        session.refresh(marketplace)
    return marketplace


def _ensure_meesho_marketplace(session: Session) -> Marketplace:
    """Fetch the seeded MEESHO row, or create it inline — mirrors
    `_ensure_marketplace` above but for Meesho (DESIGN.md §2.2: 1 split/15d)."""
    marketplace = session.execute(
        select(Marketplace).where(Marketplace.code == MarketplaceCode.MEESHO)
    ).scalar_one_or_none()
    if marketplace is None:
        marketplace = Marketplace(
            id=uuid.uuid4(),
            code=MarketplaceCode.MEESHO,
            display_name="Meesho",
            settlement_frequency_days=15,
            payout_split_count=1,
            active=True,
        )
        session.add(marketplace)
        session.commit()
        session.refresh(marketplace)
    return marketplace


def _create_products(session: Session, rng: random.Random, seller_id: uuid.UUID) -> list[Product]:
    products: list[Product] = []
    for i, (category_primary, category_sub, gst_rate) in enumerate(CATEGORIES, start=1):
        mrp_paise = rng.randint(29_900, 4_999_00)
        cost_price_paise = int(mrp_paise * rng.uniform(0.45, 0.70))
        product = Product(
            id=uuid.uuid4(),
            seller_id=seller_id,
            internal_sku=f"SKU-{i:03d}",
            product_name=f"{category_sub.split('/')[-1]} Item {i}",
            hsn_code=str(rng.randint(1000, 9999)),
            category_primary=category_primary,
            category_sub=category_sub,
            weight_grams=rng.randint(50, 5000),
            mrp_paise=mrp_paise,
            cost_price_paise=cost_price_paise,
            gst_rate=gst_rate,
        )
        session.add(product)
        products.append(product)
    return products


def _create_listings(
    session: Session, products: list[Product], account_id: uuid.UUID
) -> dict[uuid.UUID, SKUMarketplaceListing]:
    """One SKUMarketplaceListing per product, 1:1 — DESIGN.md §2.7 note."""
    listings: dict[uuid.UUID, SKUMarketplaceListing] = {}
    for product in products:
        listing = SKUMarketplaceListing(
            id=uuid.uuid4(),
            product_id=product.id,
            seller_marketplace_account_id=account_id,
            marketplace_sku_id=product.internal_sku,
            selling_price_current_paise=product.mrp_paise,
            listing_status=ListingStatus.ACTIVE,
        )
        session.add(listing)
        listings[product.id] = listing
    return listings


def _create_orders(
    session: Session,
    rng: random.Random,
    account_id: uuid.UUID,
    products: list[Product],
    listings: dict[uuid.UUID, SKUMarketplaceListing],
) -> list[Order]:
    order_statuses = [
        OrderStatus.DELIVERED,
        OrderStatus.DELIVERED,
        OrderStatus.DELIVERED,
        OrderStatus.SHIPPED,
        OrderStatus.PLACED,
        OrderStatus.RETURNED,
        OrderStatus.RTO,
        OrderStatus.CANCELLED,
    ]
    payment_types = [PaymentType.PREPAID, PaymentType.PREPAID, PaymentType.COD]
    zones = list(ShippingZone)

    orders: list[Order] = []
    for i in range(1, M_ORDERS + 1):
        product = rng.choice(products)
        quantity = rng.randint(1, 3)
        unit_price = product.mrp_paise
        gst_rate = product.gst_rate
        unit_gst_amount = (unit_price * quantity * gst_rate) // 100
        line_total = unit_price * quantity + unit_gst_amount
        order_date = PERIOD_START + timedelta(days=rng.randint(0, PERIOD_DAYS - 1))

        order = Order(
            id=uuid.uuid4(),
            seller_marketplace_account_id=account_id,
            marketplace_order_id=f"AMZ-ORD-{i:04d}",
            buyer_pincode=f"{rng.randint(100000, 999999)}",
            buyer_state=rng.choice(INDIAN_STATES),
            order_date=order_date,
            order_status=rng.choice(order_statuses),
            payment_type=rng.choice(payment_types),
            total_gross_amount_paise=line_total,
            total_gst_amount_paise=unit_gst_amount,
            shipping_zone=rng.choice(zones),
        )
        session.add(order)

        line_item = OrderLineItem(
            id=uuid.uuid4(),
            order_id=order.id,
            sku_marketplace_listing_id=listings[product.id].id,
            quantity=quantity,
            unit_price_before_gst_paise=unit_price,
            unit_gst_rate=gst_rate,
            unit_gst_amount_paise=unit_gst_amount,
            line_total_paise=line_total,
        )
        session.add(line_item)
        orders.append(order)

    return orders


def _create_flipkart_orders(
    session: Session,
    rng: random.Random,
    account_id: uuid.UUID,
    products: list[Product],
    listings: dict[uuid.UUID, SKUMarketplaceListing],
) -> list[Order]:
    """Mirrors `_create_orders` but for the Flipkart account — its own 50
    Order+OrderLineItem set with a distinct `marketplace_order_id` template
    (DESIGN.md §11.5: orders are scoped to one seller_marketplace_account_id,
    so this cannot share Amazon's order set). Kept as its own function rather
    than parameterizing `_create_orders`, per §11.5's "do not refactor" note."""
    order_statuses = [
        OrderStatus.DELIVERED,
        OrderStatus.DELIVERED,
        OrderStatus.DELIVERED,
        OrderStatus.SHIPPED,
        OrderStatus.PLACED,
        OrderStatus.RETURNED,
        OrderStatus.RTO,
        OrderStatus.CANCELLED,
    ]
    payment_types = [PaymentType.PREPAID, PaymentType.PREPAID, PaymentType.COD]
    zones = list(ShippingZone)

    orders: list[Order] = []
    for i in range(1, M_ORDERS + 1):
        product = rng.choice(products)
        quantity = rng.randint(1, 3)
        unit_price = product.mrp_paise
        gst_rate = product.gst_rate
        unit_gst_amount = (unit_price * quantity * gst_rate) // 100
        line_total = unit_price * quantity + unit_gst_amount
        order_date = PERIOD_START + timedelta(days=rng.randint(0, PERIOD_DAYS - 1))

        order = Order(
            id=uuid.uuid4(),
            seller_marketplace_account_id=account_id,
            marketplace_order_id=f"FK-ORD-{i:04d}",
            buyer_pincode=f"{rng.randint(100000, 999999)}",
            buyer_state=rng.choice(INDIAN_STATES),
            order_date=order_date,
            order_status=rng.choice(order_statuses),
            payment_type=rng.choice(payment_types),
            total_gross_amount_paise=line_total,
            total_gst_amount_paise=unit_gst_amount,
            shipping_zone=rng.choice(zones),
        )
        session.add(order)

        line_item = OrderLineItem(
            id=uuid.uuid4(),
            order_id=order.id,
            sku_marketplace_listing_id=listings[product.id].id,
            quantity=quantity,
            unit_price_before_gst_paise=unit_price,
            unit_gst_rate=gst_rate,
            unit_gst_amount_paise=unit_gst_amount,
            line_total_paise=line_total,
        )
        session.add(line_item)
        orders.append(order)

    return orders


def _create_meesho_orders(
    session: Session,
    rng: random.Random,
    account_id: uuid.UUID,
    products: list[Product],
    listings: dict[uuid.UUID, SKUMarketplaceListing],
) -> list[Order]:
    """Mirrors `_create_orders` but for the Meesho account — see
    `_create_flipkart_orders`'s docstring for why this is a parallel
    function rather than a shared, parameterized one."""
    order_statuses = [
        OrderStatus.DELIVERED,
        OrderStatus.DELIVERED,
        OrderStatus.DELIVERED,
        OrderStatus.SHIPPED,
        OrderStatus.PLACED,
        OrderStatus.RETURNED,
        OrderStatus.RTO,
        OrderStatus.CANCELLED,
    ]
    payment_types = [PaymentType.PREPAID, PaymentType.PREPAID, PaymentType.COD]
    zones = list(ShippingZone)

    orders: list[Order] = []
    for i in range(1, M_ORDERS + 1):
        product = rng.choice(products)
        quantity = rng.randint(1, 3)
        unit_price = product.mrp_paise
        gst_rate = product.gst_rate
        unit_gst_amount = (unit_price * quantity * gst_rate) // 100
        line_total = unit_price * quantity + unit_gst_amount
        order_date = PERIOD_START + timedelta(days=rng.randint(0, PERIOD_DAYS - 1))

        order = Order(
            id=uuid.uuid4(),
            seller_marketplace_account_id=account_id,
            marketplace_order_id=f"MSH-ORD-{i:04d}",
            buyer_pincode=f"{rng.randint(100000, 999999)}",
            buyer_state=rng.choice(INDIAN_STATES),
            order_date=order_date,
            order_status=rng.choice(order_statuses),
            payment_type=rng.choice(payment_types),
            total_gross_amount_paise=line_total,
            total_gst_amount_paise=unit_gst_amount,
            shipping_zone=rng.choice(zones),
        )
        session.add(order)

        line_item = OrderLineItem(
            id=uuid.uuid4(),
            order_id=order.id,
            sku_marketplace_listing_id=listings[product.id].id,
            quantity=quantity,
            unit_price_before_gst_paise=unit_price,
            unit_gst_rate=gst_rate,
            unit_gst_amount_paise=unit_gst_amount,
            line_total_paise=line_total,
        )
        session.add(line_item)
        orders.append(order)

    return orders


def _build_settlement_fixture(rng: random.Random, orders: list[Order]) -> tuple[str, dict]:
    """Build the §8-shaped settlement file content + its ground-truth summary."""
    shuffled = orders.copy()
    rng.shuffle(shuffled)
    orders_without_lines_ids = {o.id for o in shuffled[:ORDERS_WITHOUT_LINES]}
    orders_with_lines = [o for o in orders if o.id not in orders_without_lines_ids]
    assert len(orders_with_lines) == ORDERS_WITH_LINES

    rows: list[str] = []
    total_line_count = 0

    for order in orders_with_lines:
        num_lines = rng.randint(3, 6)
        descriptions = CORE_DESCRIPTIONS.copy()
        remaining = num_lines - len(descriptions)
        if remaining > 0:
            descriptions += rng.sample(EXTRA_DESCRIPTIONS, remaining)

        for description in descriptions:
            sign, (pct_low, pct_high) = FEE_DESCRIPTIONS[description]
            pct = rng.uniform(pct_low, pct_high)
            amount_paise = round(order.total_gross_amount_paise * pct)
            if sign == "negative":
                amount_paise = -amount_paise
            posted_date = order.order_date + timedelta(days=rng.randint(1, 10))
            rows.append(
                "\t".join(
                    [
                        order.marketplace_order_id,
                        TRANSACTION_TYPE_BY_DESCRIPTION[description],
                        description,
                        _money_str(amount_paise),
                        posted_date.isoformat(),
                    ]
                )
            )
            total_line_count += 1

    # Orphan lines: reference an order-id that doesn't exist in `Order` at all
    # (DESIGN.md §5 step 3: "the other discrepancy shape Phase 1 must surface").
    orphan_line_count = rng.choice([3, 4])
    for j in range(1, orphan_line_count + 1):
        description = rng.choice(["Adjustment", "Refund"])
        amount_paise = rng.choice([-1, 1]) * rng.randint(5_000, 80_000)
        posted_date = PERIOD_START + timedelta(days=rng.randint(0, PERIOD_DAYS - 1))
        rows.append(
            "\t".join(
                [
                    ORPHAN_ORDER_ID_TEMPLATE.format(j),
                    TRANSACTION_TYPE_BY_DESCRIPTION[description],
                    description,
                    _money_str(amount_paise),
                    posted_date.isoformat(),
                ]
            )
        )
        total_line_count += 1

    header = "order-id\ttransaction-type\tamount-description\tamount\tposted-date"
    file_content = "\n".join([header, *rows]) + "\n"

    ground_truth = {
        "total_orders": M_ORDERS,
        "orders_with_settlement_lines": ORDERS_WITH_LINES,
        "orders_without_settlement_lines": ORDERS_WITHOUT_LINES,
        "orphan_line_count": orphan_line_count,
        "total_line_count": total_line_count,
    }
    return file_content, ground_truth


def _build_flipkart_settlement_fixture(rng: random.Random, orders: list[Order]) -> tuple[str, dict]:
    """Build the §11.2-shaped Flipkart settlement CSV content + its
    ground-truth summary. Mirrors `_build_settlement_fixture` — comma
    delimiter and Flipkart's own header/vocabulary instead of Amazon's."""
    shuffled = orders.copy()
    rng.shuffle(shuffled)
    orders_without_lines_ids = {o.id for o in shuffled[:ORDERS_WITHOUT_LINES]}
    orders_with_lines = [o for o in orders if o.id not in orders_without_lines_ids]
    assert len(orders_with_lines) == ORDERS_WITH_LINES

    rows: list[str] = []
    total_line_count = 0

    for order in orders_with_lines:
        num_lines = rng.randint(3, 6)
        descriptions = FLIPKART_CORE_DESCRIPTIONS.copy()
        remaining = num_lines - len(descriptions)
        if remaining > 0:
            descriptions += rng.sample(FLIPKART_EXTRA_DESCRIPTIONS, remaining)

        for description in descriptions:
            sign, (pct_low, pct_high) = FLIPKART_FEE_DESCRIPTIONS[description]
            pct = rng.uniform(pct_low, pct_high)
            amount_paise = round(order.total_gross_amount_paise * pct)
            if sign == "negative":
                amount_paise = -amount_paise
            posted_date = order.order_date + timedelta(days=rng.randint(1, 10))
            rows.append(
                ",".join(
                    [
                        order.marketplace_order_id,
                        FLIPKART_TRANSACTION_TYPE_BY_DESCRIPTION[description],
                        description,
                        _money_str(amount_paise),
                        posted_date.isoformat(),
                    ]
                )
            )
            total_line_count += 1

    orphan_line_count = rng.choice([3, 4])
    for j in range(1, orphan_line_count + 1):
        description = rng.choice(FLIPKART_ORPHAN_DESCRIPTIONS)
        amount_paise = rng.choice([-1, 1]) * rng.randint(5_000, 80_000)
        posted_date = PERIOD_START + timedelta(days=rng.randint(0, PERIOD_DAYS - 1))
        rows.append(
            ",".join(
                [
                    FLIPKART_ORPHAN_ORDER_ID_TEMPLATE.format(j),
                    FLIPKART_TRANSACTION_TYPE_BY_DESCRIPTION[description],
                    description,
                    _money_str(amount_paise),
                    posted_date.isoformat(),
                ]
            )
        )
        total_line_count += 1

    header = "Order ID,Event Type,Amount Head,Amount,Event Date"
    file_content = "\n".join([header, *rows]) + "\n"

    ground_truth = {
        "total_orders": M_ORDERS,
        "orders_with_settlement_lines": ORDERS_WITH_LINES,
        "orders_without_settlement_lines": ORDERS_WITHOUT_LINES,
        "orphan_line_count": orphan_line_count,
        "total_line_count": total_line_count,
    }
    return file_content, ground_truth


def _build_meesho_settlement_fixture(rng: random.Random, orders: list[Order]) -> tuple[str, dict]:
    """Build the §11.2-shaped Meesho settlement CSV content + its
    ground-truth summary. Mirrors `_build_settlement_fixture` — comma
    delimiter and Meesho's own header/vocabulary; written to disk with a
    UTF-8 BOM by the caller (`generate()`) so the fixture genuinely exercises
    BOM tolerance end to end (DESIGN.md §11.5)."""
    shuffled = orders.copy()
    rng.shuffle(shuffled)
    orders_without_lines_ids = {o.id for o in shuffled[:ORDERS_WITHOUT_LINES]}
    orders_with_lines = [o for o in orders if o.id not in orders_without_lines_ids]
    assert len(orders_with_lines) == ORDERS_WITH_LINES

    rows: list[str] = []
    total_line_count = 0

    for order in orders_with_lines:
        num_lines = rng.randint(3, 6)
        descriptions = MEESHO_CORE_DESCRIPTIONS.copy()
        remaining = num_lines - len(descriptions)
        if remaining > 0:
            descriptions += rng.sample(MEESHO_EXTRA_DESCRIPTIONS, remaining)

        for description in descriptions:
            sign, (pct_low, pct_high) = MEESHO_FEE_DESCRIPTIONS[description]
            pct = rng.uniform(pct_low, pct_high)
            amount_paise = round(order.total_gross_amount_paise * pct)
            if sign == "negative":
                amount_paise = -amount_paise
            posted_date = order.order_date + timedelta(days=rng.randint(1, 10))
            rows.append(
                ",".join(
                    [
                        order.marketplace_order_id,
                        MEESHO_TRANSACTION_TYPE_BY_DESCRIPTION[description],
                        description,
                        _money_str(amount_paise),
                        posted_date.isoformat(),
                    ]
                )
            )
            total_line_count += 1

    orphan_line_count = rng.choice([3, 4])
    for j in range(1, orphan_line_count + 1):
        description = rng.choice(MEESHO_ORPHAN_DESCRIPTIONS)
        amount_paise = rng.choice([-1, 1]) * rng.randint(5_000, 80_000)
        posted_date = PERIOD_START + timedelta(days=rng.randint(0, PERIOD_DAYS - 1))
        rows.append(
            ",".join(
                [
                    MEESHO_ORPHAN_ORDER_ID_TEMPLATE.format(j),
                    MEESHO_TRANSACTION_TYPE_BY_DESCRIPTION[description],
                    description,
                    _money_str(amount_paise),
                    posted_date.isoformat(),
                ]
            )
        )
        total_line_count += 1

    header = "Sub Order No,Reason,Description,Value,Date"
    file_content = "\n".join([header, *rows]) + "\n"

    ground_truth = {
        "total_orders": M_ORDERS,
        "orders_with_settlement_lines": ORDERS_WITH_LINES,
        "orders_without_settlement_lines": ORDERS_WITHOUT_LINES,
        "orphan_line_count": orphan_line_count,
        "total_line_count": total_line_count,
    }
    return file_content, ground_truth


def generate(seed: int = DEFAULT_SEED) -> dict:
    """Run the full generation flow for all 3 marketplaces (DESIGN.md §5 +
    §11.5). Returns `{"amazon": ground_truth, "flipkart": ground_truth,
    "meesho": ground_truth}` (each also written to disk)."""
    rng = random.Random(seed)

    with get_sync_session() as session:
        _wipe_existing_demo_data(session)
        amazon_marketplace = _ensure_marketplace(session)
        flipkart_marketplace = _ensure_flipkart_marketplace(session)
        meesho_marketplace = _ensure_meesho_marketplace(session)

        seller = Seller(
            id=uuid.uuid4(),
            legal_name="Demo Seller Pvt Ltd",
            trade_name="Demo Traders",
            email=DEMO_SELLER_EMAIL,
            hashed_password=hash_password("demo-password-123"),
        )
        session.add(seller)
        session.flush()

        # Products are seller-scoped, not marketplace-scoped (DESIGN.md §2.4)
        # — the same 15 products are reused across all 3 marketplace
        # accounts, each with its own SKUMarketplaceListing row per account.
        products = _create_products(session, rng, seller.id)
        session.flush()

        # --- Amazon (unchanged path, DESIGN.md §5) --------------------------
        amazon_account = SellerMarketplaceAccount(
            id=uuid.uuid4(),
            seller_id=seller.id,
            marketplace_id=amazon_marketplace.id,
            merchant_id_on_platform="DEMO-MERCHANT-1",
            fulfillment_type=FulfillmentType.SELF_SHIP,
        )
        session.add(amazon_account)
        session.flush()
        amazon_listings = _create_listings(session, products, amazon_account.id)
        session.commit()
        amazon_orders = _create_orders(session, rng, amazon_account.id, products, amazon_listings)
        session.commit()
        amazon_settlement_text, amazon_ground_truth = _build_settlement_fixture(
            rng, amazon_orders
        )

        # --- Flipkart (DESIGN.md §11.5) --------------------------------------
        flipkart_account = SellerMarketplaceAccount(
            id=uuid.uuid4(),
            seller_id=seller.id,
            marketplace_id=flipkart_marketplace.id,
            merchant_id_on_platform="DEMO-MERCHANT-FK-1",
            fulfillment_type=FulfillmentType.FLIPKART_ADVANTAGE,
        )
        session.add(flipkart_account)
        session.flush()
        flipkart_listings = _create_listings(session, products, flipkart_account.id)
        session.commit()
        flipkart_orders = _create_flipkart_orders(
            session, rng, flipkart_account.id, products, flipkart_listings
        )
        session.commit()
        flipkart_settlement_text, flipkart_ground_truth = _build_flipkart_settlement_fixture(
            rng, flipkart_orders
        )

        # --- Meesho (DESIGN.md §11.5) -----------------------------------------
        meesho_account = SellerMarketplaceAccount(
            id=uuid.uuid4(),
            seller_id=seller.id,
            marketplace_id=meesho_marketplace.id,
            merchant_id_on_platform="DEMO-MERCHANT-MSH-1",
            fulfillment_type=FulfillmentType.MEESHO_SUPPLIER,
        )
        session.add(meesho_account)
        session.flush()
        meesho_listings = _create_listings(session, products, meesho_account.id)
        session.commit()
        meesho_orders = _create_meesho_orders(
            session, rng, meesho_account.id, products, meesho_listings
        )
        session.commit()
        meesho_settlement_text, meesho_ground_truth = _build_meesho_settlement_fixture(
            rng, meesho_orders
        )

        seller_id = seller.id
        amazon_account_id = amazon_account.id
        flipkart_account_id = flipkart_account.id
        meesho_account_id = meesho_account.id

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    SETTLEMENT_FIXTURE_PATH.write_text(amazon_settlement_text, encoding="utf-8", newline="\n")
    GROUND_TRUTH_PATH.write_text(
        json.dumps(amazon_ground_truth, indent=2) + "\n", encoding="utf-8"
    )
    FLIPKART_SETTLEMENT_FIXTURE_PATH.write_text(
        flipkart_settlement_text, encoding="utf-8", newline="\n"
    )
    FLIPKART_GROUND_TRUTH_PATH.write_text(
        json.dumps(flipkart_ground_truth, indent=2) + "\n", encoding="utf-8"
    )
    # Meesho fixture is written WITH a UTF-8 BOM (utf-8-sig) — DESIGN.md
    # §11.5: "so the fixture genuinely exercises the BOM-tolerance path end
    # to end, not just in a unit test."
    MEESHO_SETTLEMENT_FIXTURE_PATH.write_text(
        meesho_settlement_text, encoding="utf-8-sig", newline="\n"
    )
    MEESHO_GROUND_TRUTH_PATH.write_text(
        json.dumps(meesho_ground_truth, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Seeded seller {DEMO_SELLER_EMAIL} ({seller_id})")
    print(f"Products: {N_PRODUCTS} (shared across all 3 marketplace accounts)")
    print(f"  Amazon account {amazon_account_id}: {M_ORDERS} orders")
    print(f"    Settlement fixture -> {SETTLEMENT_FIXTURE_PATH}")
    print(f"    Ground truth -> {GROUND_TRUTH_PATH}: {amazon_ground_truth}")
    print(f"  Flipkart account {flipkart_account_id}: {M_ORDERS} orders")
    print(f"    Settlement fixture -> {FLIPKART_SETTLEMENT_FIXTURE_PATH}")
    print(f"    Ground truth -> {FLIPKART_GROUND_TRUTH_PATH}: {flipkart_ground_truth}")
    print(f"  Meesho account {meesho_account_id}: {M_ORDERS} orders")
    print(f"    Settlement fixture -> {MEESHO_SETTLEMENT_FIXTURE_PATH} (UTF-8 BOM)")
    print(f"    Ground truth -> {MEESHO_GROUND_TRUTH_PATH}: {meesho_ground_truth}")

    return {
        "amazon": amazon_ground_truth,
        "flipkart": flipkart_ground_truth,
        "meesho": meesho_ground_truth,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 1 synthetic data generator (DESIGN.md §5).")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="RNG seed (default: fixed).")
    args = parser.parse_args()
    generate(seed=args.seed)


if __name__ == "__main__":
    main()
