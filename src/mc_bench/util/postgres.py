import contextlib
import os

import sqlalchemy
import sqlalchemy.engine.url
import sqlalchemy.orm.session

_SESSIONMAKER = None


def get_engine(prefix="POSTGRES_", **kwargs):
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
            engine.echo = True

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
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_managed_session():
    with managed_session() as db:
        yield db
