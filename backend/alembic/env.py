"""Alembic environment.

Migrations run synchronously against `DATABASE_URL_SYNC` (psycopg driver)
even though the app itself is async (asyncpg) — this is the simpler of the
two standard recipes (SQLAlchemy docs: "Using Asyncio with Alembic") and is
the one DESIGN.md §1 calls out as recommended, since Alembic's own
migration-running machinery is synchronous. The DSN and target metadata are
both sourced from the app itself (app.core.config.Settings and
app.all_models.Base.metadata) rather than hardcoded here or in alembic.ini,
so there is one source of truth for both.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.all_models import Base
from app.core.config import get_settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override whatever alembic.ini has (intentionally left unset there) with
# the app's own settings, so DATABASE_URL_SYNC in the environment / .env is
# the single source of truth.
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

# Target metadata for 'autogenerate' support — all 12 entities register onto
# this single MetaData instance via app.all_models's side-effect imports.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
