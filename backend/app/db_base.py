"""Single shared SQLAlchemy declarative base.

Every model module must import `Base` from here (never define its own
`DeclarativeBase` subclass) so that all 12 entities register onto one
`MetaData` instance — this is what Alembic autogenerate compares against.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
