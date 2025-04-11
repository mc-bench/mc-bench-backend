from contextlib import asynccontextmanager

import sqlalchemy

from mc_bench.auth.clients import GithubOauthClient, GoogleOauthClient
from mc_bench.models.user import AuthProvider
from mc_bench.util.postgres import get_session
from mc_bench.util.redis import RedisDatabase, get_redis_pool

from .config import settings
from .prepared_statements import COMPARISON_BATCH_QUERY, COMPARISON_BATCH_QUERY_PRIORITY

github_oauth_client = GithubOauthClient(
    client_id=settings.GITHUB_CLIENT_ID,
    client_secret=settings.GITHUB_CLIENT_SECRET,
    salt=settings.GITHUB_EMAIL_SALT,
)

google_oauth_client = GoogleOauthClient(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    redirect_uri=settings.GOOGLE_REDIRECT_URI,
)


@asynccontextmanager
async def lifespan(app):
    session = get_session()
    engine = session.bind

    # Fill cache with pool
    redis_pool = get_redis_pool(RedisDatabase.COMPARISON)

    AuthProvider.register_client_factory("github", lambda: github_oauth_client)
    AuthProvider.register_client_factory("google", lambda: google_oauth_client)

    @sqlalchemy.event.listens_for(engine, "connect")
    def prepare_statements(dbapi_connection, connection_record):
        """Prepare statements when a new connection is created in the pool"""
        cursor = dbapi_connection.cursor()
        try:
            # Prepare the standard/random query
            cursor.execute(
                f"PREPARE comparison_batch_query(integer, integer) AS {COMPARISON_BATCH_QUERY}"
            )
            # Prepare the priority-based query
            cursor.execute(
                f"PREPARE comparison_batch_query_priority(integer, integer) AS {COMPARISON_BATCH_QUERY_PRIORITY}"
            )
            dbapi_connection.commit()
        except Exception as e:
            print(f"Error preparing statements: {e}")
        finally:
            cursor.close()

    yield

    engine.dispose()
    redis_pool.close()
