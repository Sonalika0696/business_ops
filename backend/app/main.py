"""FastAPI app factory — Phase 1 skeleton only.

Feature routers are mounted incrementally as modules land (ingestion/
reconciliation routers land separately); this wires the error envelope, a
health check, and whichever routers currently exist.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Side-effect import: registers every one of the 12 model classes onto the
# shared declarative registry (app.db_base.Base) before any router/query can
# run. SQLAlchemy configures mappers lazily on first ORM use, resolving
# relationship() string references (e.g. Mapped["FeeSchedule"]) by name
# against whatever classes have actually been imported into the process at
# that point — routers/services here only import the narrow subset of model
# modules they directly touch (masters.models never imports pricing.models
# at runtime, only under TYPE_CHECKING), so without this import the first
# real query can fail with `InvalidRequestError: ... failed to locate a
# name` depending on which routes happened to be hit first. Must run before
# `create_app()` below and before any request/query.
import app.all_models  # noqa: E402, F401
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.modules.auth.router import router as auth_router
from app.modules.ingestion.router import router as ingestion_router
from app.modules.masters.router import router as masters_router
from app.modules.sellers.router import router as sellers_router
from app.ws.settlement_progress import settlement_progress_ws


def create_app() -> FastAPI:
    app = FastAPI(title="Reconciliation & Pricing Platform API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().frontend_origins_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(auth_router)
    app.include_router(sellers_router)
    app.include_router(masters_router)
    app.include_router(ingestion_router)
    app.add_api_websocket_route("/ws/settlements/{report_id}", settlement_progress_ws)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
