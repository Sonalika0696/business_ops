"""Celery application — DESIGN.md §1/§4/§9.

Broker and result backend both point at Redis (`Settings.redis_url`). Task
autodiscovery is pointed at `app.modules.ingestion.tasks`, the only Phase 1
job type (settlement parse+match). The Celery `@task`-decorated function in
that module is a thin wrapper around a plain, directly-callable function
(`process_settlement`) — DESIGN.md §4's testability clause — so tests and the
demo script never need a running broker/worker.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "reconciliation_platform",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.modules.ingestion.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # A down/unreachable broker must fail the enqueue attempt fast, not hang
    # on OS-level default TCP timeouts — the upload endpoint wraps `.delay()`
    # in try/except specifically so a broker outage doesn't 500 the request
    # (app/modules/ingestion/service.py's `_enqueue_processing`), but that
    # only helps if the attempt itself returns quickly.
    broker_connection_timeout=2,
    broker_connection_retry_on_startup=False,
    broker_transport_options={"socket_connect_timeout": 2, "socket_timeout": 2},
)

__all__ = ["celery_app"]
