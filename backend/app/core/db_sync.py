"""Sync SQLAlchemy engine + sessionmaker, for Celery task code.

DESIGN.md §9: the settlement-processing Celery task uses a **sync** session
(built from `Settings.database_url_sync`, the same psycopg DSN Alembic uses)
since Celery's default worker model is sync — the async engine (app/core/db.py)
is for the FastAPI process only. Do not import this module from async
request-handling code; use `app.core.db.get_db` there instead.
"""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

sync_engine = create_engine(settings.database_url_sync, echo=False, future=True)

SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False, autoflush=False)


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """Context-manager yielding a sync `Session`, closed on exit.

    Used by Celery task code and standalone scripts (synthetic generator,
    demo script) that need to talk to the DB outside the async request path.
    """
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()
