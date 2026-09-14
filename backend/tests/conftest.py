"""Shared pytest fixtures.

Test-isolation strategy (documented per Phase 1 task instructions): rather
than standing up a second physical database, each test that touches the
database gets its own connection + outer transaction that is rolled back at
teardown ("transaction-per-test"). This is the simplest approach that is
still correct for a solo/local dev setup: it reuses the same Postgres
instance started by `docker compose up -d` (DATABASE_URL from .env /
Settings), requires the schema to already exist (`alembic upgrade head` has
been run), and guarantees no test leaves rows behind regardless of pass/
fail, without the overhead of creating/dropping a separate `reconcile_test`
database per run.

`db_session` is provided for tests that need it; `tests/test_health.py`
doesn't touch the database at all, so it does not depend on Postgres being
reachable.
"""

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db import engine
from app.main import app as fastapi_app


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """A DB session bound to a connection whose outer transaction is rolled back after the test."""
    connection = await engine.connect()
    trans = await connection.begin()
    session_factory = async_sessionmaker(
        bind=connection, expire_on_commit=False, autoflush=False
    )
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """An httpx.AsyncClient wired directly to the FastAPI app via the ASGI transport (no server)."""
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture
async def seed_marketplaces() -> None:
    """Ensure the `Marketplace` reference rows exist before a test that needs them.

    Note this test file's requests go through the `client` fixture, which
    exercises the app's real `get_db` dependency (the actual `AsyncSessionLocal`/
    engine) rather than the rolled-back `db_session` fixture above — masters
    endpoints commit directly, same as a real run. `Marketplace` rows are
    reference/seed data (never rolled back, never deleted), so seeding here
    reuses `scripts/seed_reference_data.py`'s own idempotent
    `INSERT ... ON CONFLICT (code) DO NOTHING` rather than inserting rows
    through `db_session` (which would be gone after rollback and doesn't
    share a connection with what `client` requests see anyway).
    """
    from scripts.seed_reference_data import seed_reference_data

    await seed_reference_data()
