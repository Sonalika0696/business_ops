"""Shared parser data shapes — DESIGN.md §8/§9.

A settlement parser is a pure, synchronous function: it takes a raw file
(handle or string) and produces a `ParseResult` of structured rows plus
parse-level rejections (bad date, bad decimal amount, wrong column count).
It never touches the database and never resolves `amount-description` to a
canonical enum — that resolution (via `app.canonical.amount_mapping`) and the
`Order` lookup are business logic that belongs to the ingestion Celery task
(DESIGN.md §9 step 3), not the parser. Keeping the parser pure is what makes
it directly unit-testable on a raw string/file handle without a DB.

Only one marketplace parser exists in Phase 1 (`amazon.py`); this module
holds the shapes future marketplace parsers (Flipkart, Meesho — Phase 2+)
would also produce, so the ingestion task can stay parser-agnostic.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ParsedSettlementRow:
    """One successfully-parsed data row (header excluded, 1-indexed for error reporting)."""

    row_number: int
    order_id: str | None  # blank in the file -> None (report-level adjustment)
    transaction_type: str
    amount_description: str
    amount: Decimal  # decimal rupees, as written in the file — not yet paise
    posted_date: date
    raw_row: dict[str, str]  # the full raw row, unparsed strings — audit trail


@dataclass(frozen=True)
class RejectedRow:
    """One row that failed *structural* parsing (bad date, bad decimal amount, ...).

    Rows rejected for semantic reasons (unmapped amount_description) are
    produced later, by the ingestion task, not by the parser.
    """

    row_number: int
    raw_row: dict[str, str]
    reason: str


@dataclass(frozen=True)
class ParseResult:
    parsed_rows: list[ParsedSettlementRow]
    rejected_rows: list[RejectedRow]


class ParserError(ValueError):
    """Raised for whole-file structural problems (e.g. missing required header
    columns) that make the file impossible to parse at all — distinct from a
    per-row `RejectedRow`, which is a partial-success outcome."""
