import uuid

import sqlalchemy
from fastapi import APIRouter, Depends, HTTPException, status
from redis import StrictRedis
from sqlalchemy import select
from sqlalchemy.orm import Session

from mc_bench.apps.api.config import settings
from mc_bench.models.comparison import Comparison, Metric
from mc_bench.models.prompt import Prompt
from mc_bench.models.run import Run, Sample
from mc_bench.models.user import User
from mc_bench.server.auth import AuthManager
from mc_bench.util.postgres import get_managed_session
from mc_bench.util.redis import RedisDatabase, get_redis_client

from ..transport_types.requests import NewComparisonBatchRequest, UserComparisonRequest
from ..transport_types.responses import ComparisonBatchResponse

comparison_router = APIRouter()

MAX_BATCH_SIZE = 10

am = AuthManager(
    jwt_secret=settings.JWT_SECRET_KEY,
    jwt_algorithm=settings.ALGORITHM,
)


@comparison_router.post("/api/comparison/batch", response_model=ComparisonBatchResponse)
def get_comparison_batch(
    request: NewComparisonBatchRequest,
    user_id=Depends(am.is_authenticated),
    db: Session = Depends(get_managed_session),
):
    if request.batch_size > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="Invalid batch size",
            headers={"WWW-Authenticate": "Bearer"},
        )

    redis: StrictRedis = get_redis_client(RedisDatabase.COMPARISON)

    metric = db.scalar(
        select(Metric).where(
            Metric.external_id == request.metric_id,
        )
    )

    if not metric:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid metric id",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sample_ids = db.execute(
        sqlalchemy.text("""\
        WITH correlation_ids AS (
            SELECT
                comparison_correlation_id id
            FROM
                sample.sample
            WHERE
                active = true
            GROUP BY
                comparison_correlation_id
            HAVING
                COUNT(*) >= 2
            ORDER BY
                random()
            LIMIT :sample_count
        )
        SELECT
            sample_1.external_id sample_1,
            sample_2.external_id sample_2
        FROM
            correlation_ids
            JOIN LATERAL (
                SELECT 
                    sample.external_id,
                    sample.comparison_correlation_id
                FROM 
                    sample.sample
                WHERE 
                    active = true
                    AND comparison_correlation_id = correlation_ids.id
                ORDER BY 
                    random()
                LIMIT 1
            ) sample_1 ON sample_1.comparison_correlation_id = correlation_ids.id
            JOIN LATERAL (
                SELECT 
                    sample.external_id,
                    sample.comparison_correlation_id
                FROM 
                    sample.sample
                WHERE 
                    active = true
                    AND comparison_correlation_id = correlation_ids.id
                    AND external_id != sample_1.external_id  -- Ensure we don't select the same sample twice
                ORDER BY 
                    random()
                LIMIT 1
            ) sample_2 ON sample_2.comparison_correlation_id = correlation_ids.id
    """).bindparams(
            sample_count=request.batch_size,
        )
    )

    comparison_tokens = []
    for sample_1, sample_2 in sample_ids:
        token = uuid.uuid4()

        # Store in Redis with expiration
        redis.setex(
            f"active_comparison:{token}",
            3600,  # 1 hour expiration
            f"{metric.external_id}:{sample_1}:{sample_2}",
        )

        build_specification_query = (
            select(Prompt.build_specification)
            .join(Run, Run.prompt_id == Prompt.id)
            .join(Sample, Sample.run_id == Run.id)
            .where(Sample.external_id == sample_1)
        )

        comparison_tokens.append(
            {
                "token": token,
                "metric_id": metric.external_id,
                "samples": [sample_1, sample_2],
                "build_description": db.scalar(build_specification_query),
            }
        )

    return {
        "comparisons": comparison_tokens,
    }


@comparison_router.post("/api/comparison/result")
def post_comparison(
    request: UserComparisonRequest,
    db: Session = Depends(get_managed_session),
    user_uuid: str = Depends(am.get_current_user_uuid),
):
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()
    redis: StrictRedis = get_redis_client(RedisDatabase.COMPARISON)
    key = f"active_comparison:{request.comparison_details.token}"
    token_data = redis.getdel(key)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active comparisons found",
        )

    metric_id, sample_data = token_data.decode("utf-8").split(":", 1)
    sample_1_id, sample_2_id = map(uuid.UUID, sample_data.split(":", 1))
    samples = list(
        db.scalars(
            select(Sample).where(Sample.external_id.in_([sample_1_id, sample_2_id]))
        )
    )
    sample_1 = samples[0] if samples[0].external_id == sample_1_id else samples[1]
    sample_2 = samples[1] if samples[1].external_id == sample_1_id else samples[0]
    winning_sample = [
        sample
        for sample in samples
        if sample.external_id == request.ordered_sample_ids[0]
    ][0]

    metric = db.scalar(
        select(Metric).where(
            Metric.external_id == metric_id,
        )
    )

    comparison = Comparison(
        user_id=user.id,
        metric_id=metric.id,
        sample_1_id=sample_1.id,
        sample_2_id=sample_2.id,
        winning_sample_id=winning_sample.id,
    )
    db.add(comparison)
    db.flush()

    return {
        "ok": True,
    }
