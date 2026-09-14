"""Ingestion — DESIGN.md §8/§9 (parser), §4/§6 (upload + idempotency), §9
(the full `process_settlement` flow, including the FAILED path), and §11
(marketplace-aware mapping + Flipkart/Meesho parsers).
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.canonical.amount_mapping import load_amount_mapping, resolve_amount_canonical
from app.core.db_sync import get_sync_session
from app.core.enums import (
    AmountCanonical,
    MarketplaceCode,
    MatchStatus,
    OrderStatus,
    PaymentType,
    SettlementStatus,
)
from app.modules.ingestion.models import SettlementLineItem, SettlementReport
from app.modules.ingestion.parsers.amazon import parse_amazon_settlement_file
from app.modules.ingestion.parsers.base import ParserError
from app.modules.ingestion.parsers.flipkart import parse_flipkart_settlement_file
from app.modules.ingestion.parsers.meesho import parse_meesho_settlement_file
from app.modules.ingestion.tasks import process_settlement
from app.modules.reconciliation.models import Order

_SETTLEMENT_HEADER = "order-id\ttransaction-type\tamount-description\tamount\tposted-date"
_FLIPKART_HEADER = "Order ID,Event Type,Amount Head,Amount,Event Date"
_MEESHO_HEADER = "Sub Order No,Reason,Description,Value,Date"


def _unique_email() -> str:
    return f"seller-{uuid.uuid4().hex[:12]}@example.test"


async def _auth_headers(client: AsyncClient) -> dict:
    email = _unique_email()
    payload = {"email": email, "password": "correct-horse-1", "legal_name": "Acme Traders"}
    await client.post("/api/auth/register", json=payload)
    login_resp = await client.post(
        "/api/auth/login", json={"email": email, "password": "correct-horse-1"}
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_account(
    client: AsyncClient,
    headers: dict,
    marketplace_code: str = "AMAZON_IN",
    fulfillment_type: str = "SELF_SHIP",
) -> uuid.UUID:
    resp = await client.post(
        "/api/marketplace-accounts",
        json={
            "marketplace_code": marketplace_code,
            "merchant_id_on_platform": f"M-{uuid.uuid4().hex[:8]}",
            "fulfillment_type": fulfillment_type,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return uuid.UUID(resp.json()["id"])


def _create_order(account_id: uuid.UUID, marketplace_order_id: str, gross_paise: int) -> uuid.UUID:
    with get_sync_session() as session:
        order = Order(
            id=uuid.uuid4(),
            seller_marketplace_account_id=account_id,
            marketplace_order_id=marketplace_order_id,
            order_date=date(2026, 8, 1),
            order_status=OrderStatus.DELIVERED,
            payment_type=PaymentType.PREPAID,
            total_gross_amount_paise=gross_paise,
        )
        session.add(order)
        session.commit()
        return order.id


def _fixture_bytes(order1_id: str, order2_id: str, orphan_id: str) -> bytes:
    """A small, hand-calculable settlement file:

    - 3 lines matched to order1 (Referral fee, Shipping fee, TCS-IGST)
    - 2 lines matched to order2 (Variable closing fee, TDS Section 194-O)
    - 1 orphan line (order-id present but no such Order exists) -> UNMATCHED
    - 1 blank-order-id line -> ADJUSTMENT
    - 1 line with an unmapped amount-description -> rejected row
    """
    lines = [
        _SETTLEMENT_HEADER,
        f"{order1_id}\tOrder\tReferral fee\t-80.00\t2026-08-02",
        f"{order1_id}\tOrder\tShipping fee\t-40.00\t2026-08-02",
        f"{order1_id}\tOrder\tTCS-IGST\t-10.00\t2026-08-02",
        f"{order2_id}\tOrder\tVariable closing fee\t-15.00\t2026-08-03",
        f"{order2_id}\tOrder\tTDS Section 194-O\t-0.50\t2026-08-03",
        f"{orphan_id}\tRefund\tRefund\t-20.00\t2026-08-04",
        "\tAdjustment\tAdjustment\t5.00\t2026-08-05",
        f"{order1_id}\tOrder\tNonexistent fee type\t-1.00\t2026-08-02",
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _flipkart_fixture_bytes(order1_id: str, order2_id: str, orphan_id: str) -> bytes:
    """Flipkart analogue of `_fixture_bytes` (DESIGN.md §11.2 shape), using
    `seed_data/flipkart_amount_mapping.csv`'s vocabulary:

    - 3 lines matched to order1 (Commission, Shipping fee, TCS collected)
    - 2 lines matched to order2 (Fixed fee, TDS deducted)
    - 1 orphan line -> UNMATCHED
    - 1 blank-order-id line -> ADJUSTMENT
    - 1 line with an unmapped Amount Head -> rejected row
    """
    lines = [
        _FLIPKART_HEADER,
        f"{order1_id},Sale,Commission,-80.00,2026-08-02",
        f"{order1_id},Sale,Shipping fee,-40.00,2026-08-02",
        f"{order1_id},Sale,TCS collected,-10.00,2026-08-02",
        f"{order2_id},Sale,Fixed fee,-15.00,2026-08-03",
        f"{order2_id},Sale,TDS deducted,-0.50,2026-08-03",
        f"{orphan_id},Return,Customer refund,-20.00,2026-08-04",
        ",Adjustment,Miscellaneous adjustment,5.00,2026-08-05",
        f"{order1_id},Sale,Nonexistent fee type,-1.00,2026-08-02",
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _meesho_fixture_bytes(order1_id: str, order2_id: str, orphan_id: str) -> bytes:
    """Meesho analogue of `_fixture_bytes` (DESIGN.md §11.2 shape, UTF-8
    BOM), using `seed_data/meesho_amount_mapping.csv`'s vocabulary:

    - 3 lines matched to order1 (Commission, Shipping charge, TCS)
    - 2 lines matched to order2 (Fixed fee, TDS)
    - 1 orphan line -> UNMATCHED
    - 1 blank-order-id line -> ADJUSTMENT
    - 1 line with an unmapped Description -> rejected row

    Written with a leading UTF-8 BOM so uploading this fixture also
    exercises the ingestion task's `encoding="utf-8-sig"` file-open path
    (DESIGN.md §11.2/§11.3), not just the parser's own defensive BOM strip.
    """
    lines = [
        _MEESHO_HEADER,
        f"{order1_id},Order,Commission,-80.00,2026-08-02",
        f"{order1_id},Order,Shipping charge,-40.00,2026-08-02",
        f"{order1_id},Order,TCS,-10.00,2026-08-02",
        f"{order2_id},Order,Fixed fee,-15.00,2026-08-03",
        f"{order2_id},Order,TDS,-0.50,2026-08-03",
        f"{orphan_id},Return,Refund to customer,-20.00,2026-08-04",
        ",Adjustment,Other adjustment,5.00,2026-08-05",
        f"{order1_id},Order,Nonexistent fee type,-1.00,2026-08-02",
    ]
    return ("\n".join(lines) + "\n").encode("utf-8-sig")


# ---------------------------------------------------------------------------
# Marketplace-aware canonical mapping — DESIGN.md §11.1
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "marketplace_code",
    [MarketplaceCode.AMAZON_IN, MarketplaceCode.FLIPKART, MarketplaceCode.MEESHO],
)
def test_amount_mapping_table_covers_all_14_canonical_values(
    marketplace_code: MarketplaceCode,
) -> None:
    """DESIGN.md §11.1: "Every table independently covers all 14 enum values
    at least once ... load each table and check set(mapping.values()) ==
    set(AmountCanonical)." """
    mapping = load_amount_mapping(marketplace_code)
    assert set(mapping.values()) == set(AmountCanonical)


def test_resolve_amount_canonical_is_marketplace_scoped() -> None:
    """The same raw string can mean different things per marketplace (or be
    unmapped for one and mapped for another) — the lookup must not leak
    across marketplace tables."""
    assert resolve_amount_canonical("Referral fee", MarketplaceCode.AMAZON_IN) == (
        AmountCanonical.REFERRAL_FEE
    )
    assert resolve_amount_canonical("Referral fee", MarketplaceCode.FLIPKART) is None
    assert resolve_amount_canonical("Commission", MarketplaceCode.FLIPKART) == (
        AmountCanonical.REFERRAL_FEE
    )
    assert resolve_amount_canonical("Commission", MarketplaceCode.MEESHO) == (
        AmountCanonical.REFERRAL_FEE
    )


# ---------------------------------------------------------------------------
# Parser (pure, no DB) — DESIGN.md §8
# ---------------------------------------------------------------------------


def test_parser_well_formed_and_malformed_rows() -> None:
    content = (
        f"{_SETTLEMENT_HEADER}\n"
        "ORD-1\tOrder\tReferral fee\t-10.50\t2026-08-01\n"
        "ORD-2\tOrder\tShipping fee\tnot-a-number\t2026-08-01\n"
        "ORD-3\tOrder\tTCS-IGST\t-1.00\tnot-a-date\n"
        "\tAdjustment\tAdjustment\t5.00\t2026-08-02\n"
    )
    result = parse_amazon_settlement_file(content)
    assert len(result.parsed_rows) == 2  # the ORD-1 line + the blank-order-id line
    assert len(result.rejected_rows) == 2
    reasons = {r.reason for r in result.rejected_rows}
    assert any("invalid amount" in r for r in reasons)
    assert any("invalid posted-date" in r for r in reasons)

    parsed_order_ids = {row.order_id for row in result.parsed_rows}
    assert "ORD-1" in parsed_order_ids
    assert None in parsed_order_ids  # blank order-id -> None


def test_parser_raises_parser_error_on_missing_required_columns() -> None:
    content = "order-id\tamount\n1\t10.00\n"
    with pytest.raises(ParserError):
        parse_amazon_settlement_file(content)


def test_parser_skips_blank_lines() -> None:
    content = f"{_SETTLEMENT_HEADER}\n\nORD-1\tOrder\tReferral fee\t-10.00\t2026-08-01\n"
    result = parse_amazon_settlement_file(content)
    assert len(result.parsed_rows) == 1
    assert len(result.rejected_rows) == 0


def test_parser_malformed_column_count_rejected() -> None:
    content = f"{_SETTLEMENT_HEADER}\nORD-1\tOrder\tReferral fee\t-10.00\n"  # missing posted-date
    result = parse_amazon_settlement_file(content)
    assert len(result.parsed_rows) == 0
    assert len(result.rejected_rows) == 1
    assert "malformed row" in result.rejected_rows[0].reason


# ---------------------------------------------------------------------------
# Flipkart/Meesho parsers (pure, no DB) — DESIGN.md §11.2
# ---------------------------------------------------------------------------


def test_flipkart_parser_well_formed_and_malformed_rows() -> None:
    content = (
        f"{_FLIPKART_HEADER}\n"
        "FK-1,Sale,Commission,-10.50,2026-08-01\n"
        "FK-2,Sale,Shipping fee,not-a-number,2026-08-01\n"
        "FK-3,Sale,TCS collected,-1.00,not-a-date\n"
        ",Adjustment,Miscellaneous adjustment,5.00,2026-08-02\n"
    )
    result = parse_flipkart_settlement_file(content)
    assert len(result.parsed_rows) == 2  # the FK-1 line + the blank-order-id line
    assert len(result.rejected_rows) == 2
    reasons = {r.reason for r in result.rejected_rows}
    assert any("invalid amount" in r for r in reasons)
    assert any("invalid posted-date" in r for r in reasons)

    parsed_order_ids = {row.order_id for row in result.parsed_rows}
    assert "FK-1" in parsed_order_ids
    assert None in parsed_order_ids  # blank Order ID -> None


def test_flipkart_parser_raises_parser_error_on_missing_required_columns() -> None:
    content = "Order ID,Amount\n1,10.00\n"
    with pytest.raises(ParserError):
        parse_flipkart_settlement_file(content)


def test_flipkart_parser_tolerates_column_drift() -> None:
    """DESIGN.md §11.2: fields are looked up by header name, not position —
    a reordered header row must still parse correctly."""
    reordered_header = "Amount,Event Date,Order ID,Amount Head,Event Type"
    content = f"{reordered_header}\n-10.50,2026-08-01,FK-1,Commission,Sale\n"
    result = parse_flipkart_settlement_file(content)
    assert len(result.rejected_rows) == 0
    assert len(result.parsed_rows) == 1
    row = result.parsed_rows[0]
    assert row.order_id == "FK-1"
    assert row.amount_description == "Commission"
    assert row.transaction_type == "Sale"
    assert str(row.amount) == "-10.50"
    assert row.posted_date.isoformat() == "2026-08-01"


def test_meesho_parser_well_formed_and_malformed_rows() -> None:
    content = (
        f"{_MEESHO_HEADER}\n"
        "MSH-1,Order,Commission,-10.50,2026-08-01\n"
        "MSH-2,Order,Shipping charge,not-a-number,2026-08-01\n"
        "MSH-3,Order,TCS,-1.00,not-a-date\n"
        ",Adjustment,Other adjustment,5.00,2026-08-02\n"
    )
    result = parse_meesho_settlement_file(content)
    assert len(result.parsed_rows) == 2  # the MSH-1 line + the blank-order-id line
    assert len(result.rejected_rows) == 2
    reasons = {r.reason for r in result.rejected_rows}
    assert any("invalid amount" in r for r in reasons)
    assert any("invalid posted-date" in r for r in reasons)


def test_meesho_parser_raises_parser_error_on_missing_required_columns() -> None:
    content = "Sub Order No,Value\n1,10.00\n"
    with pytest.raises(ParserError):
        parse_meesho_settlement_file(content)


def test_meesho_parser_tolerates_column_drift() -> None:
    reordered_header = "Value,Date,Sub Order No,Description,Reason"
    content = f"{reordered_header}\n-10.50,2026-08-01,MSH-1,Commission,Order\n"
    result = parse_meesho_settlement_file(content)
    assert len(result.rejected_rows) == 0
    assert len(result.parsed_rows) == 1
    row = result.parsed_rows[0]
    assert row.order_id == "MSH-1"
    assert row.amount_description == "Commission"


def test_meesho_parser_strips_leading_bom_when_called_directly_with_a_string() -> None:
    """DESIGN.md §11.2's BOM-tolerance paragraph: this must work even when
    the parser is called directly with a raw string (bypassing the ingestion
    task's `encoding="utf-8-sig"` file-open step entirely) — the parser's own
    defensive strip of a leading '﻿' on the first header cell is what
    makes this pass."""
    content = f"﻿{_MEESHO_HEADER}\nMSH-1,Order,Commission,-10.50,2026-08-01\n"
    result = parse_meesho_settlement_file(content)
    assert len(result.rejected_rows) == 0
    assert len(result.parsed_rows) == 1
    assert result.parsed_rows[0].order_id == "MSH-1"
    assert result.parsed_rows[0].amount_description == "Commission"


# ---------------------------------------------------------------------------
# Upload + duplicate-hash detection — DESIGN.md §4/§9
# ---------------------------------------------------------------------------


async def test_upload_and_duplicate_detection(
    client: AsyncClient, seed_marketplaces: None
) -> None:
    headers = await _auth_headers(client)
    account_id = await _create_account(client, headers)

    content = (
        f"{_SETTLEMENT_HEADER}\nORD-X\tOrder\tReferral fee\t-1.00\t2026-08-01\n"
    ).encode()
    files = {"file": ("settlement.txt", content, "text/plain")}
    data = {"seller_marketplace_account_id": str(account_id)}

    first = await client.post("/api/settlements/upload", files=files, data=data, headers=headers)
    assert first.status_code == 202
    body = first.json()
    assert body["duplicate"] is False
    assert body["status"] == "UPLOADED"

    second = await client.post(
        "/api/settlements/upload", files=files, data=data, headers=headers
    )
    assert second.status_code == 200
    body2 = second.json()
    assert body2["duplicate"] is True
    assert body2["settlement_report_id"] == body["settlement_report_id"]


async def test_upload_unknown_account_404(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    content = f"{_SETTLEMENT_HEADER}\n".encode()
    files = {"file": ("settlement.txt", content, "text/plain")}
    data = {"seller_marketplace_account_id": str(uuid.uuid4())}
    resp = await client.post("/api/settlements/upload", files=files, data=data, headers=headers)
    assert resp.status_code == 404


async def test_upload_requires_auth(client: AsyncClient) -> None:
    content = f"{_SETTLEMENT_HEADER}\n".encode()
    files = {"file": ("settlement.txt", content, "text/plain")}
    data = {"seller_marketplace_account_id": str(uuid.uuid4())}
    resp = await client.post("/api/settlements/upload", files=files, data=data)
    assert resp.status_code == 401


async def test_settlement_report_scoped_to_owning_seller(
    client: AsyncClient, seed_marketplaces: None
) -> None:
    headers_a = await _auth_headers(client)
    account_id = await _create_account(client, headers_a)
    content = (
        f"{_SETTLEMENT_HEADER}\nORD-Y\tOrder\tReferral fee\t-1.00\t2026-08-01\n"
    ).encode()
    files = {"file": ("settlement.txt", content, "text/plain")}
    data = {"seller_marketplace_account_id": str(account_id)}
    upload_resp = await client.post(
        "/api/settlements/upload", files=files, data=data, headers=headers_a
    )
    report_id = upload_resp.json()["settlement_report_id"]

    headers_b = await _auth_headers(client)
    get_resp = await client.get(f"/api/settlements/{report_id}", headers=headers_b)
    assert get_resp.status_code == 404

    line_items_resp = await client.get(
        f"/api/settlements/{report_id}/line-items", headers=headers_b
    )
    assert line_items_resp.status_code == 404


# ---------------------------------------------------------------------------
# process_settlement — DESIGN.md §9's 7 steps, exact rollup math
# ---------------------------------------------------------------------------


async def test_process_settlement_matches_and_computes_rollups(
    client: AsyncClient, seed_marketplaces: None
) -> None:
    headers = await _auth_headers(client)
    account_id = await _create_account(client, headers)

    order1_str = f"ORD-{uuid.uuid4().hex[:8]}"
    order2_str = f"ORD-{uuid.uuid4().hex[:8]}"
    order3_str = f"ORD-{uuid.uuid4().hex[:8]}"  # exists, but no settlement lines
    orphan_str = f"ORD-{uuid.uuid4().hex[:8]}"  # referenced by a line, never created

    _create_order(account_id, order1_str, 100_000)
    _create_order(account_id, order2_str, 50_000)
    _create_order(account_id, order3_str, 25_000)

    content = _fixture_bytes(order1_str, order2_str, orphan_str)
    files = {"file": ("settlement.txt", content, "text/plain")}
    data = {"seller_marketplace_account_id": str(account_id)}
    upload_resp = await client.post(
        "/api/settlements/upload", files=files, data=data, headers=headers
    )
    assert upload_resp.status_code == 202
    report_id = uuid.UUID(upload_resp.json()["settlement_report_id"])

    with get_sync_session() as session:
        process_settlement(report_id, session)

    with get_sync_session() as session:
        report = session.get(SettlementReport, report_id)
        line_items = list(
            session.execute(
                select(SettlementLineItem).where(
                    SettlementLineItem.settlement_report_id == report_id
                )
            )
            .scalars()
            .all()
        )

    assert report.status == SettlementStatus.RECONCILED
    assert report.row_count == 8
    assert report.rejected_row_count == 1
    assert len(report.rejected_rows_detail) == 1
    assert "unmapped amount_description" in report.rejected_rows_detail[0]["reason"]

    assert len(line_items) == 7
    by_status: dict[MatchStatus, int] = {}
    for li in line_items:
        by_status[li.match_status] = by_status.get(li.match_status, 0) + 1
    assert by_status.get(MatchStatus.MATCHED_EXACT) == 5
    assert by_status.get(MatchStatus.UNMATCHED) == 1
    assert by_status.get(MatchStatus.ADJUSTMENT) == 1

    # Hand-calculated per DESIGN.md §9 step 5 (see docstring in _fixture_bytes):
    #   gross_sales = 100_000 + 50_000 = 150_000 (order3 excluded: no MATCHED_EXACT line)
    #   fees = -8_000 (referral) -4_000 (shipping) -1_500 (closing) +500 (adjustment) = -13_000
    #   taxes       = -1_000 (TCS) -50 (TDS) = -1_050
    #   refunds     = -2_000
    #   reimbursements = 0
    #   net_payout  = 150_000 + sum(all 7 line items) = 150_000 - 16_050 = 133_950
    assert report.total_gross_sales_paise == 150_000
    assert report.total_fees_paise == -13_000
    assert report.total_taxes_deducted_paise == -1_050
    assert report.total_returns_refunds_paise == -2_000
    assert report.total_reimbursements_paise == 0
    assert report.net_payout_expected_paise == 133_950
    assert report.net_payout_bank_credited_paise is None
    assert report.discrepancy_amount_paise is None


async def test_process_settlement_failed_path_missing_storage_file(
    client: AsyncClient, seed_marketplaces: None
) -> None:
    """DESIGN.md §9 step 7: any unhandled exception -> status=FAILED,
    error_message set, commit + publish, re-raise. The DB state must land
    correctly even though the plain function re-raises past the caller."""
    headers = await _auth_headers(client)
    account_id = await _create_account(client, headers)

    with get_sync_session() as session:
        report = SettlementReport(
            id=uuid.uuid4(),
            seller_marketplace_account_id=account_id,
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 1),
            source_file_hash=uuid.uuid4().hex + uuid.uuid4().hex,
            original_filename="missing.txt",
            storage_path="/nonexistent/path/does-not-exist-12345.txt",
            status=SettlementStatus.UPLOADED,
        )
        session.add(report)
        session.commit()
        report_id = report.id

    with get_sync_session() as session:
        with pytest.raises(Exception):  # noqa: B017 — FileNotFoundError, deliberately broad
            process_settlement(report_id, session)

    with get_sync_session() as session:
        reloaded = session.get(SettlementReport, report_id)
        assert reloaded.status == SettlementStatus.FAILED
        assert reloaded.error_message  # non-empty, set


# ---------------------------------------------------------------------------
# process_settlement — Flipkart/Meesho, DESIGN.md §11 (marketplace-aware
# mapping + parser dispatch, full upload-through-reconcile cycle)
# ---------------------------------------------------------------------------


async def test_process_settlement_flipkart_full_cycle(
    client: AsyncClient, seed_marketplaces: None
) -> None:
    """Mirrors `test_process_settlement_matches_and_computes_rollups` but for
    a Flipkart account/file shape — exercises marketplace-aware canonical
    mapping (DESIGN.md §11.1) and parser dispatch (§11.3) end to end."""
    headers = await _auth_headers(client)
    account_id = await _create_account(
        client, headers, marketplace_code="FLIPKART", fulfillment_type="FLIPKART_ADVANTAGE"
    )

    order1_str = f"FK-{uuid.uuid4().hex[:8]}"
    order2_str = f"FK-{uuid.uuid4().hex[:8]}"
    order3_str = f"FK-{uuid.uuid4().hex[:8]}"  # exists, but no settlement lines
    orphan_str = f"FK-{uuid.uuid4().hex[:8]}"  # referenced by a line, never created

    _create_order(account_id, order1_str, 100_000)
    _create_order(account_id, order2_str, 50_000)
    _create_order(account_id, order3_str, 25_000)

    content = _flipkart_fixture_bytes(order1_str, order2_str, orphan_str)
    files = {"file": ("settlement.csv", content, "text/csv")}
    data = {"seller_marketplace_account_id": str(account_id)}
    upload_resp = await client.post(
        "/api/settlements/upload", files=files, data=data, headers=headers
    )
    assert upload_resp.status_code == 202
    report_id = uuid.UUID(upload_resp.json()["settlement_report_id"])

    with get_sync_session() as session:
        process_settlement(report_id, session)

    with get_sync_session() as session:
        report = session.get(SettlementReport, report_id)
        line_items = list(
            session.execute(
                select(SettlementLineItem).where(
                    SettlementLineItem.settlement_report_id == report_id
                )
            )
            .scalars()
            .all()
        )

    assert report.status == SettlementStatus.RECONCILED
    assert report.row_count == 8
    assert report.rejected_row_count == 1
    assert "unmapped amount_description" in report.rejected_rows_detail[0]["reason"]

    assert len(line_items) == 7
    by_status: dict[MatchStatus, int] = {}
    for li in line_items:
        by_status[li.match_status] = by_status.get(li.match_status, 0) + 1
    assert by_status.get(MatchStatus.MATCHED_EXACT) == 5
    assert by_status.get(MatchStatus.UNMATCHED) == 1
    assert by_status.get(MatchStatus.ADJUSTMENT) == 1

    # Same hand-calculable shape as _fixture_bytes's Amazon docstring:
    #   gross_sales = 100_000 + 50_000 = 150_000 (order3 excluded: no MATCHED_EXACT line)
    #   fees = -8_000 (commission) -4_000 (shipping) -1_500 (fixed fee) +500 (adjustment) = -13_000
    #   taxes       = -1_000 (TCS) -50 (TDS) = -1_050
    #   refunds     = -2_000
    #   reimbursements = 0
    #   net_payout  = 150_000 + sum(all 7 line items) = 150_000 - 16_050 = 133_950
    assert report.total_gross_sales_paise == 150_000
    assert report.total_fees_paise == -13_000
    assert report.total_taxes_deducted_paise == -1_050
    assert report.total_returns_refunds_paise == -2_000
    assert report.total_reimbursements_paise == 0
    assert report.net_payout_expected_paise == 133_950


async def test_process_settlement_meesho_full_cycle_with_bom(
    client: AsyncClient, seed_marketplaces: None
) -> None:
    """Mirrors `test_process_settlement_matches_and_computes_rollups` but for
    a Meesho account/file shape written with a UTF-8 BOM — exercises the
    ingestion task's `encoding="utf-8-sig"` file-open path end to end
    (DESIGN.md §11.2/§11.3), on top of marketplace-aware canonical mapping."""
    headers = await _auth_headers(client)
    account_id = await _create_account(
        client, headers, marketplace_code="MEESHO", fulfillment_type="MEESHO_SUPPLIER"
    )

    order1_str = f"MSH-{uuid.uuid4().hex[:8]}"
    order2_str = f"MSH-{uuid.uuid4().hex[:8]}"
    order3_str = f"MSH-{uuid.uuid4().hex[:8]}"  # exists, but no settlement lines
    orphan_str = f"MSH-{uuid.uuid4().hex[:8]}"  # referenced by a line, never created

    _create_order(account_id, order1_str, 100_000)
    _create_order(account_id, order2_str, 50_000)
    _create_order(account_id, order3_str, 25_000)

    content = _meesho_fixture_bytes(order1_str, order2_str, orphan_str)
    assert content.startswith(b"\xef\xbb\xbf")  # confirm the fixture really carries a BOM
    files = {"file": ("settlement.csv", content, "text/csv")}
    data = {"seller_marketplace_account_id": str(account_id)}
    upload_resp = await client.post(
        "/api/settlements/upload", files=files, data=data, headers=headers
    )
    assert upload_resp.status_code == 202
    report_id = uuid.UUID(upload_resp.json()["settlement_report_id"])

    with get_sync_session() as session:
        process_settlement(report_id, session)

    with get_sync_session() as session:
        report = session.get(SettlementReport, report_id)
        line_items = list(
            session.execute(
                select(SettlementLineItem).where(
                    SettlementLineItem.settlement_report_id == report_id
                )
            )
            .scalars()
            .all()
        )

    assert report.status == SettlementStatus.RECONCILED
    assert report.row_count == 8
    assert report.rejected_row_count == 1
    assert "unmapped amount_description" in report.rejected_rows_detail[0]["reason"]

    assert len(line_items) == 7
    by_status: dict[MatchStatus, int] = {}
    for li in line_items:
        by_status[li.match_status] = by_status.get(li.match_status, 0) + 1
    assert by_status.get(MatchStatus.MATCHED_EXACT) == 5
    assert by_status.get(MatchStatus.UNMATCHED) == 1
    assert by_status.get(MatchStatus.ADJUSTMENT) == 1

    assert report.total_gross_sales_paise == 150_000
    assert report.total_fees_paise == -13_000
    assert report.total_taxes_deducted_paise == -1_050
    assert report.total_returns_refunds_paise == -2_000
    assert report.total_reimbursements_paise == 0
    assert report.net_payout_expected_paise == 133_950
