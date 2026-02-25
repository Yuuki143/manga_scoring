"""Alembic environment configuration for MMIP database migrations.

Supports both offline (SQL script generation) and online (direct DB connection)
migration modes. All ORM models are imported to ensure their tables are
registered with Base.metadata before autogenerate introspects the schema.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# Alembic Config object — gives access to alembic.ini values
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging if present
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Import all models so that Base.metadata is fully populated
# ---------------------------------------------------------------------------
# This import registers every ORM model against the shared DeclarativeBase.
# If new models are added to app/models/ they should be imported here (or
# re-exported from app/models/__init__.py, which is already done).
import app.models  # noqa: F401 — side-effect import to register all mappers

from app.database import Base

target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Override the SQLAlchemy URL from application settings so we don't have to
# hard-code credentials inside alembic.ini.
# ---------------------------------------------------------------------------
from app.config import settings  # noqa: E402

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


# ---------------------------------------------------------------------------
# Offline migration mode
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    In this mode Alembic emits SQL to stdout (or a file) rather than
    executing it against a live database.  This is useful for generating
    reviewed migration scripts before applying them to production.

    The call to ``context.execute()`` here emits the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migration mode
# ---------------------------------------------------------------------------


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this mode a real database ``Connection`` is acquired from an
    ``Engine`` and migrations are executed within a transaction.
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
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
