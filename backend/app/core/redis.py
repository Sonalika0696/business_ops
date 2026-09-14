"""Redis client factories, for Celery result peeking / WS pub-sub.

Two flavors: an async client (`get_redis`) for the FastAPI process — used by
the settlement-progress WS route to subscribe — and a sync client
(`get_redis_sync`) for Celery task code, which runs sync (DESIGN.md §9) and
needs to publish progress frames to the same `settlement:{id}` channel.

Both set an explicit short connect/socket timeout. Without one, redis-py
falls back to the OS-level default TCP timeout (which can be tens of
seconds) and, worse, retries that full timeout on every connection attempt
under its default retry policy — so every fail-open publish (DESIGN.md §4:
Redis being down must never fail the job) would still stall the caller for a
long time per call, defeating the point of "fail open". A short explicit
timeout keeps the fail-open path actually fast.
"""

from functools import lru_cache

import redis as redis_sync
from redis.asyncio import Redis

from app.core.config import get_settings

_CONNECT_TIMEOUT_SECONDS = 0.3


@lru_cache
def get_redis() -> Redis:
    """Cached async Redis client, built from settings.redis_url."""
    settings = get_settings()
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=_CONNECT_TIMEOUT_SECONDS,
        socket_timeout=_CONNECT_TIMEOUT_SECONDS,
        retry_on_timeout=False,
        retry_on_error=[],
    )


@lru_cache
def get_redis_sync() -> redis_sync.Redis:
    """Cached sync Redis client, built from settings.redis_url — for Celery task code."""
    settings = get_settings()
    return redis_sync.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=_CONNECT_TIMEOUT_SECONDS,
        socket_timeout=_CONNECT_TIMEOUT_SECONDS,
        retry_on_timeout=False,
        retry_on_error=[],
    )
