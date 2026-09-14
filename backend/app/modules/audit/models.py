"""AuditEvent — DESIGN.md §2.12. Hash-chained, append-only, tamper-evident.

Global hash chain (one chain across all entities, ordered by created_at /
insertion). `entity_type`/`entity_id` are a polymorphic reference (not a DB
FK) since the target can be any of several tables. Insert-only: the future
`append_audit_event(...)` service function (app/modules/audit/service.py)
is meant to be the only way rows are created — no direct inserts elsewhere,
and no delete column exists on this table at all.
"""

import uuid
from datetime import datetime

from sqlalchemy import CHAR, DateTime, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db_base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(Text, nullable=False)  # 'system' or seller id/email
    before_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # null only for the very first event ever
    previous_event_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    # sha256(previous_event_hash + canonical_json(payload))
    this_event_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
