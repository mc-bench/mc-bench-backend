import uuid
from typing import List

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
from mc_bench.util.logging import get_logger
from mc_bench.util.postgres import get_managed_session
from mc_bench.util.redis import RedisDatabase, get_redis_database

from ..celery import send_task
from ..transport_types.requests import NewComparisonBatchRequest, UserComparisonRequest
from ..transport_types.responses import ComparisonBatchResponse, MetricResponse

logger = get_logger(__name__)
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
    redis: StrictRedis = Depends(get_redis_database(RedisDatabase.COMPARISON)),
):
    if request.batch_size > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="Invalid batch size",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
        WITH approval_state AS (
            SELECT
                id approved_state_id
            FROM
                scoring.sample_approval_state
            WHERE
                name = 'APPROVED'
        ),
        correlation_ids AS (
            SELECT
                comparison_correlation_id id
            FROM
                sample.sample
                cross join approval_state
            WHERE
                sample.approval_state_id = approval_state.approved_state_id
            GROUP BY
                comparison_correlation_id
            HAVING
                COUNT(*) >= 2
            ORDER BY
                random()
            LIMIT :sample_count
        )
        SELECT
            sample_1.comparison_sample_id sample_1,
            sample_2.comparison_sample_id sample_2
        FROM
            correlation_ids
            JOIN LATERAL (
                SELECT 
                    sample.comparison_sample_id,
                    sample.comparison_correlation_id
                FROM 
                    sample.sample
                    cross join approval_state
                WHERE
                    sample.approval_state_id = approval_state.approved_state_id
                    AND sample.comparison_correlation_id = correlation_ids.id
                ORDER BY 
                    random()
                LIMIT 1
            ) sample_1 ON sample_1.comparison_correlation_id = correlation_ids.id
            JOIN LATERAL (
                SELECT 
                    sample.comparison_sample_id,
                    sample.comparison_correlation_id
                FROM 
                    sample.sample
                    cross join approval_state
                WHERE 
                    sample.approval_state_id = approval_state.approved_state_id
                    AND sample.comparison_correlation_id = correlation_ids.id
                    AND sample.comparison_sample_id != sample_1.comparison_sample_id  -- Ensure we don't select the same sample twice
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
            .where(Sample.comparison_sample_id == sample_1)
        )

        sample_1_artifact = db.scalar(
            select(Sample).where(Sample.comparison_sample_id == sample_1)
        ).get_comparison_artifact()

        sample_2_artifact = db.scalar(
            select(Sample).where(Sample.comparison_sample_id == sample_2)
        ).get_comparison_artifact()

        # assets = []
        # for sample_id in [sample_1, sample_2]:
        #     assets.append({
        #         "sample_id": sample_id,
        #         "files": [
        #             {
        #                 "kind": "gltf_scene",
        #                 "url": random.choice([
        #                     "/my_awesome_house.gltf",
        #                     "/my_cool_house.gltf"
        #                 ])
        #             }
        #         ]
        #     })

        assets = [
            {
                "sample_id": sample_1,
                "files": [
                    {
                        "kind": "gltf_scene",
                        "url": "/my_awesome_house.gltf",
                        "bucket": settings.EXTERNAL_OBJECT_BUCKET,
                        "key": sample_1_artifact.key,
                    },
                ],
            },
            {
                "sample_id": sample_2,
                "files": [
                    {
                        "kind": "gltf_scene",
                        "url": "/my_cool_house.gltf",
                        "bucket": settings.EXTERNAL_OBJECT_BUCKET,
                        "key": sample_2_artifact.key,
                    }
                ],
            },
        ]

        comparison_tokens.append(
            {
                "token": token,
                "metric_id": metric.external_id,
                "samples": [sample_1, sample_2],
                "build_description": db.scalar(build_specification_query),
                "assets": assets,
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
    redis: StrictRedis = Depends(get_redis_database(RedisDatabase.COMPARISON)),
):
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()
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
            select(Sample).where(
                Sample.comparison_sample_id.in_([sample_1_id, sample_2_id])
            )
        )
    )

    try:
        assert len(samples) == 2
        assert sample_1_id != sample_2_id
        assert set(request.ordered_sample_ids) == {sample_1_id, sample_2_id}
        assert request.ordered_sample_ids[0] in [sample_1_id, sample_2_id]

    except AssertionError as e:
        # TODO: error log this
        logger.error("AssertionError", error=e)

        return {
            "ok": False,
        }
        # It's ok if we silently ignore this for now
        # raise HTTPException(
        #     status_code=status.HTTP_400_BAD_REQUEST,
        #     detail="Invalid comparison request",
        # )

    sample_lookup = {sample.comparison_sample_id: sample for sample in samples}
    sample_1 = sample_lookup[sample_1_id]
    sample_2 = sample_lookup[sample_2_id]

    winning_sample = sample_lookup[request.ordered_sample_ids[0]]

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

    sample_1_run = db.scalar(
        select(Sample).where(Sample.comparison_sample_id == sample_1_id)
    ).run

    sample_2_run = db.scalar(
        select(Sample).where(Sample.comparison_sample_id == sample_2_id)
    ).run

    if redis.set("elo_calculation_in_progress", "1", ex=300, nx=True):
        logger.info("Enqueuing elo calculation task")
        send_task("elo_calculation")
    else:
        logger.debug("Elo calculation already in progress")

    return {
        "sample_1_model": sample_1_run.model.slug,
        "sample_2_model": sample_2_run.model.slug,
    }


# @comparison_router.get("/api/sample/asset_details", response_model=SamplesAssetDetailResponse)
# def get_samples_asset_details(
#     request: SamplesAssetDetailRequest
# ):
#     assets = []
#
#     for sample_id in request.ordered_sample_ids:
#         assets.append({
#             "sample_id": sample_id,
#             "files": [
#                 {
#                     "kind": "gltf_scene",
#                     "url": random.choice([
#                         "/my_awesome_house.gltf",
#                         "/my_cool_house.gltf"
#                     ])
#                 }
#             ]
#         })
#
#     return {
#         "assets": assets,
#     }


@comparison_router.get(
    "/api/metric",
    response_model=List[MetricResponse],
)
def get_metrics(
    db: Session = Depends(get_managed_session),
):
    return map(lambda x: x.to_dict(), db.scalars(select(Metric)).all())
