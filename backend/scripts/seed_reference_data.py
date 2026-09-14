"""Seed the `Marketplace` reference rows (DESIGN.md §2.2).

Standalone script — not part of the running app. Uses the same async
engine/session as the app (app.core.db). Idempotent: uses
`INSERT ... ON CONFLICT (code) DO NOTHING`, so re-running it never
duplicates rows (Marketplace.code is unique).

Usage:
    uv run python scripts/seed_reference_data.py
"""

import asyncio
import sys
from pathlib import Path

# Allow running as `python scripts/seed_reference_data.py` (not just
# `python -m scripts.seed_reference_data`) by ensuring the backend/ root
# (the parent of this scripts/ dir) is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Side-effect import: registers every model class on the shared declarative
# registry before any mapper is used. Marketplace has string-typed
# relationships (e.g. to FeeSchedule) that only resolve if the referenced
# module has actually been imported somewhere — without this, configuring
# Marketplace's mapper raises InvalidRequestError the first time it's queried.
import app.all_models  # noqa: F401
from app.core.db import AsyncSessionLocal
from app.core.enums import MarketplaceCode
from app.modules.masters.models import Marketplace

# Placeholder cadences per DESIGN.md §2.2 — adjust from real marketplace
# docs if/when found later.
REFERENCE_MARKETPLACES: list[dict] = [
    {
        "code": MarketplaceCode.AMAZON_IN,
        "display_name": "Amazon India",
        "settlement_frequency_days": 14,
        "payout_split_count": 1,
        "active": True,
    },
    {
        "code": MarketplaceCode.FLIPKART,
        "display_name": "Flipkart",
        "settlement_frequency_days": 7,
        "payout_split_count": 2,
        "active": True,
    },
    {
        "code": MarketplaceCode.MEESHO,
        "display_name": "Meesho",
        "settlement_frequency_days": 15,
        "payout_split_count": 1,
        "active": True,
    },
]


async def seed_reference_data() -> None:
    async with AsyncSessionLocal() as session:
        for row in REFERENCE_MARKETPLACES:
            stmt = (
                pg_insert(Marketplace)
                .values(**row)
                .on_conflict_do_nothing(index_elements=[Marketplace.code])
            )
            await session.execute(stmt)
        await session.commit()

        result = await session.execute(select(Marketplace).order_by(Marketplace.code))
        rows = result.scalars().all()
        print(f"Marketplace reference rows present ({len(rows)}):")
        for m in rows:
            print(
                f"  {m.code.value:12s} display_name={m.display_name!r} "
                f"settlement_frequency_days={m.settlement_frequency_days} "
                f"payout_split_count={m.payout_split_count} active={m.active}"
            )


if __name__ == "__main__":
    asyncio.run(seed_reference_data())
