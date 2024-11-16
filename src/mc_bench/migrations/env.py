import logging.config
import sys
from sqlalchemy import pool
from alembic import context
from mc_bench.schema.postgres import metadata
from mc_bench.util.postgres import get_engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

target_metadata = metadata

# Dictionary-based logging configuration
logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "generic": {
            "format": "%(levelname)-5.5s [%(name)s] %(message)s",
            "datefmt": "%H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stderr,
            "level": "NOTSET",
            "formatter": "generic",
        }
    },
    "loggers": {
        "root": {"level": "WARNING", "handlers": ["console"], "qualname": ""},
        "sqlalchemy.engine": {
            "level": "WARNING",
            "handlers": [],
            "qualname": "sqlalchemy.engine",
        },
        "alembic": {"level": "INFO", "handlers": [], "qualname": "alembic"},
    },
    "root": {"level": "WARNING", "handlers": ["console"]},
}

# Apply the configuration
logging.config.dictConfig(logging_config)


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = get_engine(
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            dialect_opts={"paramstyle": "named"},
            include_schemas=True,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("Only online mode supported.")
else:
    run_migrations_online()
