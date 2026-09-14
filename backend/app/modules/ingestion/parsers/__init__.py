"""Parser dispatch — DESIGN.md §11.3.

Maps a `MarketplaceCode` to its settlement-file parser function. The
ingestion task (`app.modules.ingestion.tasks`) uses this to pick the right
parser for a given `SettlementReport` instead of hardcoding Amazon's. An
unregistered marketplace code is a programming error (all 3 seeded
marketplaces have parsers below) — a `KeyError` on lookup is intentionally
allowed to propagate rather than being silently skipped.
"""

from collections.abc import Callable, Iterable

from app.core.enums import MarketplaceCode
from app.modules.ingestion.parsers.amazon import parse_amazon_settlement_file
from app.modules.ingestion.parsers.base import ParseResult
from app.modules.ingestion.parsers.flipkart import parse_flipkart_settlement_file
from app.modules.ingestion.parsers.meesho import parse_meesho_settlement_file

PARSERS: dict[MarketplaceCode, Callable[[Iterable[str] | str], ParseResult]] = {
    MarketplaceCode.AMAZON_IN: parse_amazon_settlement_file,
    MarketplaceCode.FLIPKART: parse_flipkart_settlement_file,
    MarketplaceCode.MEESHO: parse_meesho_settlement_file,
}

__all__ = ["PARSERS"]
