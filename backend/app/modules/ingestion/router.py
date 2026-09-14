"""Ingestion routes — DESIGN.md §6.

    POST   /api/settlements/upload                    -> 202 { settlement_report_id, status }
                                                           (200 + duplicate:true on repeat hash)
    GET    /api/settlements                                  -> 200 { items, total }
    GET    /api/settlements/{id}                              -> 200 SettlementReport
    GET    /api/settlements/{id}/line-items  ?match_status=    -> 200 { items, total }
    GET    /api/settlements/{id}/rejected-rows                  -> 200 { items }

All routes are auth-guarded (`get_current_seller`) and seller-scoped via the
owning `SellerMarketplaceAccount`; a settlement report belonging to another
seller's account 404s, matching the masters module's pattern (never 403 —
don't leak existence).
"""

import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_seller
from app.core.enums import MatchStatus
from app.modules.ingestion import service
from app.modules.ingestion.schemas import (
    RejectedRowsResponse,
    SettlementLineItemListResponse,
    SettlementReportListResponse,
    SettlementReportRead,
    SettlementUploadResponse,
)
from app.modules.sellers.models import Seller

router = APIRouter(tags=["ingestion"])

_NOT_FOUND_DETAIL = {"code": "not_found", "message": "Resource not found.", "field_errors": None}


def _pagination(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> tuple[int, int]:
    return page, page_size


@router.post(
    "/api/settlements/upload",
    response_model=SettlementUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_settlement(
    response: Response,
    file: UploadFile = File(...),
    seller_marketplace_account_id: uuid.UUID = Form(...),
    current_seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> SettlementUploadResponse:
    content = await file.read()
    try:
        report, duplicate = await service.upload_settlement_file(
            db,
            current_seller.id,
            seller_marketplace_account_id,
            file.filename or "settlement.txt",
            content,
        )
    except service.AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_DETAIL
        ) from exc

    if duplicate:
        # DESIGN.md §4: duplicate upload -> 200 OK with the existing report,
        # not the 202 Accepted a freshly-enqueued upload gets.
        response.status_code = status.HTTP_200_OK

    return SettlementUploadResponse(
        settlement_report_id=report.id, status=report.status, duplicate=duplicate
    )


@router.get("/api/settlements", response_model=SettlementReportListResponse)
async def list_settlements(
    pagination: tuple[int, int] = Depends(_pagination),
    current_seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> SettlementReportListResponse:
    page, page_size = pagination
    items, total = await service.list_settlement_reports(db, current_seller.id, page, page_size)
    return SettlementReportListResponse(items=items, total=total)


@router.get("/api/settlements/{report_id}", response_model=SettlementReportRead)
async def get_settlement(
    report_id: uuid.UUID,
    current_seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> SettlementReportRead:
    try:
        return await service.get_settlement_report(db, current_seller.id, report_id)
    except service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_DETAIL
        ) from exc


@router.get(
    "/api/settlements/{report_id}/line-items", response_model=SettlementLineItemListResponse
)
async def list_settlement_line_items(
    report_id: uuid.UUID,
    match_status: MatchStatus | None = Query(default=None),
    pagination: tuple[int, int] = Depends(_pagination),
    current_seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> SettlementLineItemListResponse:
    page, page_size = pagination
    try:
        items, total = await service.list_settlement_line_items(
            db, current_seller.id, report_id, match_status, page, page_size
        )
    except service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_DETAIL
        ) from exc
    return SettlementLineItemListResponse(items=items, total=total)


@router.get(
    "/api/settlements/{report_id}/rejected-rows", response_model=RejectedRowsResponse
)
async def get_rejected_rows(
    report_id: uuid.UUID,
    current_seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> RejectedRowsResponse:
    try:
        rows = await service.get_rejected_rows(db, current_seller.id, report_id)
    except service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_DETAIL
        ) from exc
    return RejectedRowsResponse(items=rows)
