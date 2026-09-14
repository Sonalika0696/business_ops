"""Import every module's models.py purely for side-effect table registration.

Alembic's env.py imports this module (not the individual model modules) so
that `Base.metadata` is fully populated before autogenerate compares it
against the live database. Nothing here needs to be used directly — the
imports themselves are the point (ruff: noqa F401).
"""

from app.db_base import Base  # noqa: F401
from app.modules.audit.models import AuditEvent  # noqa: F401
from app.modules.ingestion.models import SettlementLineItem, SettlementReport  # noqa: F401
from app.modules.masters.models import Marketplace, Product, SellerMarketplaceAccount  # noqa: F401
from app.modules.pricing.models import FeeSchedule, SKUMarketplaceListing  # noqa: F401
from app.modules.reconciliation.models import Order, OrderLineItem  # noqa: F401
from app.modules.returns.models import Return  # noqa: F401
from app.modules.sellers.models import Seller  # noqa: F401
