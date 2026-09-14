"""Flipkart settlement file parser — DESIGN.md §11.2 (frozen file shape).

Comma-separated, UTF-8, header row required:

    Order ID,Event Type,Amount Head,Amount,Event Date

Pure/synchronous, no DB access — takes an iterable of lines (a file handle
opened in text mode, or `str.splitlines()`) and returns a `ParseResult`.
`amount` is left as a `Decimal` (decimal rupees, as written) — conversion to
signed integer paise and canonical-enum resolution happen in the ingestion
task (DESIGN.md §9 step 3 / §11.3), not here. Mirrors `amazon.py`'s exact
structure — only the delimiter and column names differ.
"""

import csv
from collections.abc import Iterable
from datetime import date
from decimal import Decimal, InvalidOperation

from app.modules.ingestion.parsers.base import (
    ParsedSettlementRow,
    ParserError,
    ParseResult,
    RejectedRow,
)

EXPECTED_COLUMNS: tuple[str, ...] = (
    "Order ID",
    "Event Type",
    "Amount Head",
    "Amount",
    "Event Date",
)


def parse_flipkart_settlement_file(source: Iterable[str] | str) -> ParseResult:
    """Parse the Flipkart CSV shape (DESIGN.md §11.2).

    `source` is either a raw string (the whole file content) or an iterable
    of lines (e.g. an open file handle). Raises `ParserError` if the header
    row is missing required columns — a whole-file problem, not a per-row
    one. Per-row structural problems (malformed amount/date, wrong column
    count) become `RejectedRow`s rather than raising, per DESIGN.md §9/
    ARCHITECTURE.md §11 ("partial success is a first-class outcome").

    BOM tolerance (DESIGN.md §11.2): a leading UTF-8 BOM character on the
    first header cell is stripped defensively here, on top of the ingestion
    task opening the file with `encoding="utf-8-sig"` — this parser can be
    (and is, in tests) called directly with a raw string that still carries
    a BOM, so BOM handling must not depend solely on how the caller opened
    the file.
    """
    lines: Iterable[str] = source.splitlines() if isinstance(source, str) else source

    reader = csv.reader(lines, delimiter=",")
    try:
        header = [col.strip() for col in next(reader)]
    except StopIteration:
        # Empty file: no header, no rows — nothing to reject either.
        return ParseResult(parsed_rows=[], rejected_rows=[])

    if header:
        header[0] = header[0].lstrip("﻿")

    missing_columns = [col for col in EXPECTED_COLUMNS if col not in header]
    if missing_columns:
        raise ParserError(
            f"settlement file missing required column(s): {', '.join(missing_columns)}"
        )

    parsed_rows: list[ParsedSettlementRow] = []
    rejected_rows: list[RejectedRow] = []

    for row_number, raw_fields in enumerate(reader, start=1):
        if not raw_fields or all(not field.strip() for field in raw_fields):
            continue  # skip blank lines silently — not data, not an error

        if len(raw_fields) != len(header):
            rejected_rows.append(
                RejectedRow(
                    row_number=row_number,
                    raw_row={"_raw_columns": raw_fields},
                    reason=(
                        f"malformed row: expected {len(header)} columns, got {len(raw_fields)}"
                    ),
                )
            )
            continue

        raw_row = dict(zip(header, raw_fields, strict=True))

        order_id_raw = raw_row.get("Order ID", "").strip()
        order_id = order_id_raw or None
        transaction_type = raw_row.get("Event Type", "").strip()
        amount_description = raw_row.get("Amount Head", "").strip()
        amount_raw = raw_row.get("Amount", "").strip()
        posted_date_raw = raw_row.get("Event Date", "").strip()

        if not amount_description:
            rejected_rows.append(RejectedRow(row_number, raw_row, "missing Amount Head"))
            continue

        try:
            amount = Decimal(amount_raw)
        except (InvalidOperation, ValueError):
            rejected_rows.append(
                RejectedRow(row_number, raw_row, f"invalid amount: {amount_raw!r}")
            )
            continue

        try:
            posted_date = date.fromisoformat(posted_date_raw)
        except ValueError:
            rejected_rows.append(
                RejectedRow(row_number, raw_row, f"invalid posted-date: {posted_date_raw!r}")
            )
            continue

        parsed_rows.append(
            ParsedSettlementRow(
                row_number=row_number,
                order_id=order_id,
                transaction_type=transaction_type,
                amount_description=amount_description,
                amount=amount,
                posted_date=posted_date,
                raw_row=raw_row,
            )
        )

    return ParseResult(parsed_rows=parsed_rows, rejected_rows=rejected_rows)


__all__ = ["EXPECTED_COLUMNS", "parse_flipkart_settlement_file"]
