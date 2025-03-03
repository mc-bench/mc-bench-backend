import contextlib
import os
import traceback

import sqlalchemy
import sqlalchemy.engine.url
import sqlalchemy.orm.session

from mc_bench.util.logging import get_logger

logger = get_logger(__name__)

_SESSIONMAKER = None


def get_engine(prefix="POSTGRES_", **kwargs):
    logger.info("Getting engine", prefix=prefix)
    url = sqlalchemy.engine.url.URL(
        host=os.environ[f"{prefix}HOST"],
        port=int(os.environ[f"{prefix}PORT"]),
        username=os.environ[f"{prefix}USER"],
        password=os.environ[f"{prefix}PASSWORD"],
        database=os.environ[f"{prefix}DB"],
        drivername=os.environ.get(f"{prefix}DRIVERNAME", "postgresql+psycopg2"),
        query=os.environ.get(f"{prefix}QUERY", {}),
    )

    kwargs.setdefault("pool_pre_ping", True)

    kwargs.setdefault("connect_args", {})
    kwargs["connect_args"]["sslmode"] = kwargs["connect_args"].pop(
        "sslmode", os.environ.get(f"{prefix}SSLMODE", "require")
    )
    return sqlalchemy.create_engine(url, **kwargs)


def get_session(engine=None, **kwargs):
    global _SESSIONMAKER

    if _SESSIONMAKER is not None:
        if engine is None:
            return _SESSIONMAKER()
        else:
            Session = sqlalchemy.orm.session.sessionmaker(bind=engine)
            return Session()
    else:
        if engine is None:
            engine = get_engine(**kwargs)
            engine.echo = (
                True if os.environ.get("SHOW_VERBOSE_SQL") == "true" else False
            )

        Session = sqlalchemy.orm.session.sessionmaker(bind=engine)
        _SESSIONMAKER = Session
        return _SESSIONMAKER()


def get_sessionmaker():
    global _SESSIONMAKER

    # TODO: This is a hack to get the side effect of having a global sessionmaker made
    get_session()

    return _SESSIONMAKER


@contextlib.contextmanager
def managed_session():
    session = get_session()
    try:
        yield session
        logger.debug("Committing session")
        session.commit()
        logger.debug("Session committed")
    except Exception:
        logger.error("Rolling back session", error=traceback.format_exc())
        session.rollback()
        logger.info("Session rolled back")
        raise
    finally:
        logger.debug("Closing session")
        session.close()


def get_managed_session():
    logger.debug("Getting managed session")
    with managed_session() as db:
        logger.info("Yielding managed session")
        yield db
    logger.debug("Exited managed session")
