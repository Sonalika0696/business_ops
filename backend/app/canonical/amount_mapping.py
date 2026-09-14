"""Config-not-code loader for the raw amount-description -> canonical enum table.

DESIGN.md §8 / §11.1: the mapping lives as data (one CSV per marketplace under
`seed_data/`), not as branching code. Different marketplaces use different
vocabulary for the same fee concept (e.g. Amazon's "Referral fee" vs.
Flipkart/Meesho's "Commission" both mean `REFERRAL_FEE`), so the lookup is
marketplace-aware: `load_amount_mapping`/`resolve_amount_canonical` both take
a `MarketplaceCode` and consult that marketplace's own table only. An
unmapped description is never guessed at or silently dropped — the caller
(ingestion parser/task) is responsible for treating a lookup miss as a
rejected row.
"""

import csv
from functools import lru_cache
from pathlib import Path

from app.core.enums import AmountCanonical, MarketplaceCode

_SEED_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "seed_data"

_MAPPING_CSV_PATH_BY_MARKETPLACE: dict[MarketplaceCode, Path] = {
    MarketplaceCode.AMAZON_IN: _SEED_DATA_DIR / "amazon_amount_mapping.csv",
    MarketplaceCode.FLIPKART: _SEED_DATA_DIR / "flipkart_amount_mapping.csv",
    MarketplaceCode.MEESHO: _SEED_DATA_DIR / "meesho_amount_mapping.csv",
}


@lru_cache
def load_amount_mapping(marketplace_code: MarketplaceCode) -> dict[str, AmountCanonical]:
    """Load raw_description -> AmountCanonical for one marketplace, keyed
    lower-cased for case-insensitive lookup.

    Cached (`lru_cache`, keyed on `marketplace_code` — `MarketplaceCode` is a
    hashable `StrEnum`, so this works unchanged) — each table is read once
    per process. Tests that need a fresh read of a table can call
    `load_amount_mapping.cache_clear()`.
    """
    csv_path = _MAPPING_CSV_PATH_BY_MARKETPLACE[marketplace_code]
    mapping: dict[str, AmountCanonical] = {}
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw = row["raw_description"].strip()
            canonical = AmountCanonical(row["canonical"].strip())
            mapping[raw.lower()] = canonical
    return mapping


def resolve_amount_canonical(
    raw_description: str, marketplace_code: MarketplaceCode
) -> AmountCanonical | None:
    """Case-insensitive exact-match lookup within one marketplace's table.

    Returns None on a miss — caller rejects the row.
    """
    return load_amount_mapping(marketplace_code).get(raw_description.strip().lower())
