from contextlib import asynccontextmanager

from mc_bench.auth.clients import GithubOauthClient
from mc_bench.models.user import AuthProvider
from mc_bench.util.postgres import get_session
from mc_bench.util.redis import RedisDatabase, get_redis_pool

from .config import settings

github_oauth_client = GithubOauthClient(
    client_id=settings.GITHUB_CLIENT_ID,
    client_secret=settings.GITHUB_CLIENT_SECRET,
    salt=settings.GITHUB_EMAIL_SALT,
)


@asynccontextmanager
async def lifespan(app):
    session = get_session()
    engine = session.bind
    redis_pool = get_redis_pool(RedisDatabase.COMPARISON)
    AuthProvider.register_client_factory("github", lambda: github_oauth_client)

    yield

    engine.dispose()
    redis_pool.close()
