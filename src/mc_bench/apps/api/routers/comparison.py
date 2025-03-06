import uuid
from functools import lru_cache
from typing import List, Optional

import sqlalchemy
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from redis import StrictRedis
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

import mc_bench.schema.postgres as schema
from mc_bench.apps.api.config import settings
from mc_bench.auth.permissions import PERM
from mc_bench.models.comparison import (
    Comparison,
    ComparisonRank,
    Metric,
    ModelLeaderboard,
    PromptLeaderboard,
    SampleLeaderboard,
)
from mc_bench.models.model import Model
from mc_bench.models.prompt import Prompt, Tag
from mc_bench.models.run import Artifact, Run, Sample, TestSet
from mc_bench.models.user import User
from mc_bench.server.auth import AuthManager
from mc_bench.util.logging import get_logger
from mc_bench.util.postgres import get_managed_session
from mc_bench.util.redis import RedisDatabase, get_redis_database

from ..celery import send_task
from ..transport_types.requests import NewComparisonBatchRequest, UserComparisonRequest
from ..transport_types.responses import (
    ArtifactResponse,
    ComparisonBatchResponse,
    LeaderboardEntryResponse,
    LeaderboardResponse,
    MetricResponse,
    ModelResponse,
    PagingResponse,
    PromptLeaderboardEntryResponse,
    PromptLeaderboardResponse,
    PromptResponse,
    RunInfoResponse,
    SampleResponse,
    SampleStatsResponse,
    TagResponse,
    TestSetResponse,
    TopSampleResponse,
)

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
    request_obj: Request,
    response: Response,
    user_id: Optional[str] = Depends(am.maybe_authenticated),
    db: Session = Depends(get_managed_session),
    redis: StrictRedis = Depends(get_redis_database(RedisDatabase.COMPARISON)),
):
    # Process session and identification headers
    if user_id is None:
        test_set_id = db.scalar(
            select(TestSet.id).where(TestSet.name == "Unauthenticated Test Set")
        )
        am.process_session_headers(request_obj, response, db)
    else:
        test_set_id = db.scalar(
            select(TestSet.id).where(TestSet.name == "Authenticated Test Set")
        )
        am.process_session_headers(
            request_obj,
            response,
            db,
            user=db.scalar(select(User).where(User.external_id == user_id)),
        )

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

    # try:
    sample_data = db.execute(
        sqlalchemy.text(
            "EXECUTE comparison_batch_query(:test_set_id, :sample_count)"
        ).bindparams(
            sample_count=request.batch_size,
            test_set_id=test_set_id,
        )
    ).fetchall()

    comparison_tokens = []
    for (
        sample_1,
        sample_1_key,
        sample_2,
        sample_2_key,
        build_specification,
    ) in sample_data:
        token = uuid.uuid4()

        # Store in Redis with expiration
        redis.setex(
            f"active_comparison:{token}",
            3600,  # 1 hour expiration
            f"{metric.external_id}:{sample_1}:{sample_2}",
        )

        assets = [
            {
                "sample_id": sample_1,
                "files": [
                    {
                        "kind": "gltf_scene",
                        "bucket": settings.EXTERNAL_OBJECT_BUCKET,
                        "key": sample_1_key,
                    },
                ],
            },
            {
                "sample_id": sample_2,
                "files": [
                    {
                        "kind": "gltf_scene",
                        "bucket": settings.EXTERNAL_OBJECT_BUCKET,
                        "key": sample_2_key,
                    }
                ],
            },
        ]

        comparison_tokens.append(
            {
                "token": token,
                "metric_id": metric.external_id,
                "samples": [sample_1, sample_2],
                "build_description": build_specification,
                "assets": assets,
            }
        )
    return {
        "comparisons": comparison_tokens,
    }


@comparison_router.post("/api/comparison/result")
def post_comparison(
    request: UserComparisonRequest,
    request_obj: Request,
    response: Response,
    db: Session = Depends(get_managed_session),
    user_uuid: Optional[str] = Depends(am.maybe_authenticated),
    redis: StrictRedis = Depends(get_redis_database(RedisDatabase.COMPARISON)),
):
    # Process session and identification headers
    user = None
    can_vote = True  # Default for anonymous users

    if user_uuid:
        user = db.scalars(select(User).where(User.external_id == user_uuid)).one()
        session_id, identification_token_id = am.process_session_headers(
            request_obj, response, db, user=user
        )
        # For authenticated users, check if they have voting permission
        can_vote = PERM.VOTING.VOTE in user.scopes
    else:
        session_id, identification_token_id = am.process_session_headers(
            request_obj, response, db
        )

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

    sample_lookup = {sample.comparison_sample_id: sample for sample in samples}
    sample_1 = sample_lookup[sample_1_id]
    sample_2 = sample_lookup[sample_2_id]

    ranks = []
    for idx, sample_or_samples in enumerate(request.ordered_sample_ids):
        rank = idx + 1

        if isinstance(sample_or_samples, list):
            for ranked_sample_id in sample_or_samples:
                ranks.append((rank, sample_lookup[ranked_sample_id]))
        else:
            ranks.append((rank, sample_lookup[sample_or_samples]))

    metric = db.scalar(
        select(Metric).where(
            Metric.external_id == metric_id,
        )
    )

    # Get test_set_id from one of the samples
    test_set_id = None
    if sample_1.test_set_id:
        test_set_id = sample_1.test_set_id
    elif sample_2.test_set_id:
        test_set_id = sample_2.test_set_id

    # Create a comparison record if user is anonymous or has voting permissions
    if can_vote:
        # Create a comparison record
        comparison = Comparison(
            user_id=user.id if user else None,  # None for anonymous users
            metric_id=metric.id,
            test_set_id=test_set_id,
            session_id=session_id,
            identification_token_id=identification_token_id,
        )
        db.add(comparison)
        db.flush()

        # Add rank records for each sample
        for rank, sample in ranks:
            db.add(
                ComparisonRank(
                    comparison_id=comparison.id,
                    sample_id=sample.id,
                    rank=rank,
                )
            )

        # Trigger ELO calculation if needed
        if redis.set("elo_calculation_in_progress", "1", ex=300, nx=True):
            logger.info("Enqueuing elo calculation task")
            send_task("elo_calculation")
        else:
            logger.debug("Elo calculation already in progress")

    # Return model names for the UI
    return {
        "sample_1_model": sample_1.run.model.name,
        "sample_2_model": sample_2.run.model.name,
    }


@lru_cache(maxsize=1)
def _cached_metrics(db: Session):
    """Cache the metrics to avoid hitting the database repeatedly."""
    return list(map(lambda x: x.to_dict(), db.scalars(select(Metric)).all()))


@lru_cache(maxsize=1)
def _cached_test_sets(db: Session):
    """Cache the test sets to avoid hitting the database repeatedly."""
    return list(map(lambda x: x.to_dict(), db.scalars(select(TestSet)).all()))


@lru_cache(maxsize=1)
def _cached_tags(db: Session):
    """Cache the tags to avoid hitting the database repeatedly."""
    return list(map(lambda x: x.to_dict(), db.scalars(select(Tag)).all()))


@comparison_router.get(
    "/api/metric",
    response_model=List[MetricResponse],
)
def get_metrics(
    db: Session = Depends(get_managed_session),
):
    """List all metrics, cached in memory to avoid database hits."""
    return _cached_metrics(db)


@comparison_router.get(
    "/api/leaderboard/metric",
    response_model=List[MetricResponse],
)
def get_leaderboard_metrics(
    db: Session = Depends(get_managed_session),
):
    """List all metrics for leaderboards, cached in memory to avoid database hits."""
    return _cached_metrics(db)


@comparison_router.get(
    "/api/leaderboard/test-set",
    response_model=List[TestSetResponse],
)
def get_test_sets(
    db: Session = Depends(get_managed_session),
):
    """List all test sets, cached in memory to avoid database hits."""
    return _cached_test_sets(db)


@comparison_router.get(
    "/api/leaderboard/tag",
    response_model=List[TagResponse],
)
def get_tags(
    db: Session = Depends(get_managed_session),
):
    """List all tags used for prompts, cached in memory to avoid database hits."""
    return _cached_tags(db)


@comparison_router.get(
    "/api/leaderboard/{metric_id}/{test_set_id}",
    response_model=LeaderboardResponse,
)
def get_leaderboard(
    metric_id: uuid.UUID,
    test_set_id: uuid.UUID,
    tag_id: Optional[uuid.UUID] = None,
    limit: int = Query(20, ge=1, le=100),
    min_votes: int = Query(10, ge=0),
    db: Session = Depends(get_managed_session),
):
    """
    Get the leaderboard for a specific metric and test set.

    If tag_id is provided, returns the tag-specific leaderboard.
    Otherwise, returns the global leaderboard (no tag filter).
    """
    # Verify the metric exists
    metric = db.scalar(select(Metric).where(Metric.external_id == metric_id))
    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metric not found",
        )

    # Verify the test set exists
    test_set = db.scalar(select(TestSet).where(TestSet.external_id == test_set_id))
    if not test_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test set not found",
        )

    # Check if tag exists when tag_id is provided
    tag = None
    if tag_id:
        tag = db.scalar(select(Tag).where(Tag.external_id == tag_id))
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found",
            )

    # Query for leaderboard entries
    query = (
        select(ModelLeaderboard)
        .where(
            ModelLeaderboard.metric_id == metric.id,
            ModelLeaderboard.test_set_id == test_set.id,
            ModelLeaderboard.vote_count >= min_votes,
        )
        .order_by(ModelLeaderboard.elo_score.desc())
        .limit(limit)
    )

    # Add tag filter if tag_id is provided
    if tag_id:
        query = query.where(ModelLeaderboard.tag_id == tag.id)
    else:
        query = query.where(ModelLeaderboard.tag_id == None)

    # Execute query
    entries = db.scalars(query).all()

    # Transform entries to response format
    leaderboard_entries = []
    for entry in entries:
        model_data = ModelResponse(
            id=entry.model.external_id, name=entry.model.name, slug=entry.model.slug
        )

        tag_data = None
        if entry.tag:
            tag_data = TagResponse(id=entry.tag.external_id, name=entry.tag.name)

        leaderboard_entries.append(
            LeaderboardEntryResponse(
                elo_score=entry.elo_score,
                vote_count=entry.vote_count,
                win_count=entry.win_count,
                loss_count=entry.loss_count,
                tie_count=entry.tie_count,
                last_updated=entry.last_updated.isoformat(),
                model=model_data,
                tag=tag_data,
            )
        )

    return LeaderboardResponse(
        metric=metric.to_dict(),
        test_set_id=test_set.external_id,
        test_set_name=test_set.name,
        entries=leaderboard_entries,
    )


@comparison_router.get(
    "/api/leaderboard/{metric_id}/{test_set_id}/{model_id}/stats",
    response_model=dict,
)
def get_model_sample_stats(
    metric_id: uuid.UUID,
    test_set_id: uuid.UUID,
    model_id: uuid.UUID,
    tag_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_managed_session),
):
    """
    Get statistics about sample performance for a specific model.

    This provides deeper insight into how samples from this model are performing,
    including quartile win rates and other statistics.
    """
    # Verify all entities exist
    metric = db.scalar(select(Metric).where(Metric.external_id == metric_id))
    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metric not found",
        )

    test_set = db.scalar(select(TestSet).where(TestSet.external_id == test_set_id))
    if not test_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test set not found",
        )

    model = db.scalar(select(Model).where(Model.external_id == model_id))
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Get model entry in leaderboard
    model_entry_query = select(ModelLeaderboard).where(
        ModelLeaderboard.model_id == model.id,
        ModelLeaderboard.metric_id == metric.id,
        ModelLeaderboard.test_set_id == test_set.id,
    )

    # Add tag filter if tag_id is provided
    if tag_id:
        tag = db.scalar(select(Tag).where(Tag.external_id == tag_id))
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found",
            )
        model_entry_query = model_entry_query.where(ModelLeaderboard.tag_id == tag.id)
    else:
        model_entry_query = model_entry_query.where(ModelLeaderboard.tag_id == None)

    model_entry = db.scalar(model_entry_query)
    if not model_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found in leaderboard",
        )

    # Get sample entries with prompt information
    sample_query = (
        select(SampleLeaderboard, Sample, Run, Prompt)
        .join(Sample, SampleLeaderboard.sample_id == Sample.id)
        .join(Run, Sample.run_id == Run.id)
        .join(Prompt, Run.prompt_id == Prompt.id)
        .where(
            Sample.run.has(model_id=model.id),
            SampleLeaderboard.metric_id == metric.id,
            SampleLeaderboard.test_set_id == test_set.id,
        )
        .order_by(SampleLeaderboard.elo_score.desc())
    )

    sample_entries = db.execute(sample_query).all()

    # Calculate statistics
    total_samples = len(sample_entries)
    if total_samples == 0:
        return {
            "model": model.to_dict(),
            "sample_count": 0,
            "statistics": {"message": "No sample data available for this model"},
        }

    # Sort samples by ELO score for bucket calculation
    sorted_by_elo = sorted(sample_entries, key=lambda x: x[0].elo_score, reverse=True)

    # Calculate statistics with 10 buckets (deciles) instead of quartiles
    bucket_size = max(1, total_samples // 10)

    # Calculate statistics by bucket
    buckets = []
    for i in range(10):
        start_idx = i * bucket_size
        end_idx = min(start_idx + bucket_size, total_samples)
        if start_idx >= total_samples:
            break

        bucket_samples = sorted_by_elo[start_idx:end_idx]

        # Calculate aggregate statistics for this bucket
        total_votes = sum(sample[0].vote_count for sample in bucket_samples)
        total_wins = sum(sample[0].win_count for sample in bucket_samples)
        total_losses = sum(sample[0].loss_count for sample in bucket_samples)
        total_ties = sum(sample[0].tie_count for sample in bucket_samples)

        win_rate = total_wins / total_votes if total_votes > 0 else 0

        buckets.append(
            {
                "bucket": i + 1,
                "sample_count": len(bucket_samples),
                "avg_elo": sum(sample[0].elo_score for sample in bucket_samples)
                / len(bucket_samples),
                "win_rate": win_rate,
                "total_votes": total_votes,
                "total_wins": total_wins,
                "total_losses": total_losses,
                "total_ties": total_ties,
                "model_name": model.name,
            }
        )

    # Transform top 20 samples to include prompt information
    top_samples = []
    for sample_entry in sorted_by_elo[:20]:  # Top 20 samples
        sample_leaderboard, sample, run, prompt = sample_entry
        win_rate = (
            sample_leaderboard.win_count / sample_leaderboard.vote_count
            if sample_leaderboard.vote_count > 0
            else 0
        )

        top_samples.append(
            TopSampleResponse(
                id=sample.external_id,
                elo_score=sample_leaderboard.elo_score,
                win_rate=win_rate,
                vote_count=sample_leaderboard.vote_count,
                prompt_id=prompt.external_id,
                prompt_name=prompt.name,
            ).dict()
        )

    # Return statistics
    return {
        "model": model.to_dict(),
        "sample_count": total_samples,
        "global_stats": {
            "avg_elo": sum(sample[0].elo_score for sample in sample_entries)
            / total_samples,
            "total_votes": sum(sample[0].vote_count for sample in sample_entries),
            "total_wins": sum(sample[0].win_count for sample in sample_entries),
            "total_losses": sum(sample[0].loss_count for sample in sample_entries),
            "total_ties": sum(sample[0].tie_count for sample in sample_entries),
            "win_rate": sum(sample[0].win_count for sample in sample_entries)
            / sum(sample[0].vote_count for sample in sample_entries)
            if sum(sample[0].vote_count for sample in sample_entries) > 0
            else 0,
        },
        "bucket_stats": buckets,
        "top_samples": top_samples,
    }


@comparison_router.get(
    "/api/leaderboard/{metric_id}/{test_set_id}/{model_id}/prompts",
    response_model=PromptLeaderboardResponse,
)
def get_model_prompt_leaderboard(
    metric_id: uuid.UUID,
    test_set_id: uuid.UUID,
    model_id: uuid.UUID,
    tag_id: Optional[uuid.UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    min_votes: int = Query(5, ge=0),
    db: Session = Depends(get_managed_session),
):
    """
    Get paginated prompt leaderboard data for a specific model.

    Returns ELO scores and statistics for prompts used with this model,
    showing which prompts produce the best results for this specific model.
    """
    # Verify all entities exist
    metric = db.scalar(select(Metric).where(Metric.external_id == metric_id))
    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metric not found",
        )

    test_set = db.scalar(select(TestSet).where(TestSet.external_id == test_set_id))
    if not test_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test set not found",
        )

    model = db.scalar(select(Model).where(Model.external_id == model_id))
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Build query for prompt leaderboard entries related to this model
    # We need to retrieve all prompts used by this model
    prompts_used_by_model = (
        select(Prompt.id)
        .join(
            schema.specification.run, Prompt.id == schema.specification.run.c.prompt_id
        )
        .where(schema.specification.run.c.model_id == model.id)
        .group_by(Prompt.id)
    ).subquery()

    base_query = select(PromptLeaderboard).where(
        PromptLeaderboard.prompt_id.in_(prompts_used_by_model),
        PromptLeaderboard.metric_id == metric.id,
        PromptLeaderboard.test_set_id == test_set.id,
        PromptLeaderboard.vote_count >= min_votes,
    )

    # Add tag filter if tag_id is provided
    if tag_id:
        tag = db.scalar(select(Tag).where(Tag.external_id == tag_id))
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found",
            )
        base_query = base_query.where(PromptLeaderboard.tag_id == tag.id)
    else:
        base_query = base_query.where(PromptLeaderboard.tag_id == None)

    # Get total count for pagination
    count_query = select(func.count()).select_from(base_query.subquery())
    total_items = db.scalar(count_query) or 0

    # Calculate pagination parameters
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 1
    offset = (page - 1) * page_size

    # Add pagination
    query = (
        base_query.order_by(PromptLeaderboard.elo_score.desc())
        .offset(offset)
        .limit(page_size)
    )

    # Execute query
    entries = db.scalars(query).all()

    # Transform entries to response format
    leaderboard_entries = []
    for entry in entries:
        prompt = db.scalar(select(Prompt).where(Prompt.id == entry.prompt_id))
        if not prompt:
            continue

        tag_data = None
        if entry.tag:
            tag_data = TagResponse(id=entry.tag.external_id, name=entry.tag.name)

        leaderboard_entries.append(
            PromptLeaderboardEntryResponse(
                elo_score=entry.elo_score,
                vote_count=entry.vote_count,
                win_count=entry.win_count,
                loss_count=entry.loss_count,
                tie_count=entry.tie_count,
                last_updated=entry.last_updated.isoformat(),
                prompt_id=prompt.external_id,
                prompt_name=prompt.name,
                tag=tag_data,
            )
        )

    # Create paging response
    paging = PagingResponse(
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        total_items=total_items,
        has_next=page < total_pages,
        has_previous=page > 1,
    )

    # Return leaderboard response
    return PromptLeaderboardResponse(
        metric=metric.to_dict(),
        test_set_id=test_set.external_id,
        test_set_name=test_set.name,
        model_id=model.external_id,
        model_name=model.name,
        entries=leaderboard_entries,
        paging=paging,
    )


@comparison_router.get(
    "/api/sample/{external_id}",
    response_model=SampleResponse,
)
def view_sample(
    external_id: str,
    db: Session = Depends(get_managed_session),
):
    """
    Get public information about a sample.

    This endpoint is unauthenticated and provides non-sensitive details about a sample,
    including its experimental and approval states. It returns performance statistics
    if the sample is included in a test set and has leaderboard data.

    Only samples that are complete (is_complete=true) and not pending (is_pending=false)
    are accessible through this endpoint, regardless of their approval state.
    """
    # Query sample with necessary relationships loaded
    query = (
        select(Sample)
        .where(Sample.external_id == external_id)
        .options(
            # Load the run and its relationships - we need to do this differently
            selectinload(Sample.run).joinedload(Run.model),
            selectinload(Sample.run).joinedload(Run.prompt).joinedload(Prompt.tags),
            selectinload(Sample.run).joinedload(Run.template),
            selectinload(Sample.artifacts).joinedload(Artifact.kind),
            selectinload(Sample.test_set),
            selectinload(Sample.approval_state),
            selectinload(Sample.experimental_state),
        )
    )

    sample = db.scalar(query)
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample with ID {external_id} not found",
        )

    # Check if sample is complete and not pending
    if sample.is_pending or not sample.is_complete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This sample is not available for public viewing",
        )

    # Create artifact responses for appropriate artifacts
    # Only include specific artifact types that are relevant for the frontend
    public_artifact_kinds = [
        "RENDERED_MODEL_GLB",
        "RENDERED_MODEL_GLB_COMPARISON_SAMPLE",
        "NORTHSIDE_CAPTURE_PNG",
        "SOUTHSIDE_CAPTURE_PNG",
        "EASTSIDE_CAPTURE_PNG",
        "WESTSIDE_CAPTURE_PNG",
    ]

    artifacts = [
        ArtifactResponse(
            id=artifact.external_id,
            kind=artifact.kind.name,
            bucket=artifact.bucket,
            key=artifact.key,
        )
        for artifact in sample.artifacts
        if artifact.kind.name in public_artifact_kinds
    ]

    # Get sample statistics if it's in the leaderboard
    sample_stats = None

    # Find the metric to use (usually we want the primary metric for the frontend)
    # First, try to find all metrics to see what we have
    all_metrics = db.scalars(select(Metric)).all()
    logger.info(f"Available metrics: {[m.name for m in all_metrics]}")

    # Try to find the standard metric
    primary_metric = db.scalar(select(Metric).where(Metric.name == "Build Quality"))
    if not primary_metric:
        logger.info("'Build Quality' metric not found, looking for alternatives")
        # Let's try to find a metric with a similar name
        for name in ["quality", "build", "score"]:
            primary_metric = db.scalar(
                select(Metric).where(Metric.name.ilike(f"%{name}%"))
            )
            if primary_metric:
                logger.info(f"Found alternative metric: {primary_metric.name}")
                break

        # If still not found, fallback to any metric
        if not primary_metric and all_metrics:
            primary_metric = all_metrics[0]
            logger.info(f"Using fallback metric: {primary_metric.name}")
    else:
        logger.info("Found 'Build Quality' metric")

    # Log information about test set
    if sample.test_set_id:
        logger.info(f"Sample has test_set_id: {sample.test_set_id}")
    else:
        logger.info("Sample does not have a test_set_id")

    if primary_metric and sample.test_set_id:
        # Look up sample stats in the leaderboard
        logger.info(
            f"Looking for stats with sample_id={sample.id}, metric_id={primary_metric.id}, test_set_id={sample.test_set_id}"
        )

        # First try to see if any sample leaderboard entries exist at all
        all_sample_entries = db.scalars(
            select(SampleLeaderboard).where(SampleLeaderboard.sample_id == sample.id)
        ).all()

        if all_sample_entries:
            logger.info(
                f"Found {len(all_sample_entries)} leaderboard entries for this sample"
            )
            for entry in all_sample_entries:
                logger.info(
                    f"Entry: metric_id={entry.metric_id}, test_set_id={entry.test_set_id}"
                )
        else:
            logger.info("No leaderboard entries found for this sample")

        # Now try our specific query
        sample_leaderboard = db.scalar(
            select(SampleLeaderboard).where(
                SampleLeaderboard.sample_id == sample.id,
                SampleLeaderboard.metric_id == primary_metric.id,
                SampleLeaderboard.test_set_id == sample.test_set_id,
            )
        )

        if sample_leaderboard:
            logger.info("Found matching leaderboard entry, creating stats response")
            win_rate = (
                sample_leaderboard.win_count / sample_leaderboard.vote_count
                if sample_leaderboard.vote_count > 0
                else 0
            )
            sample_stats = SampleStatsResponse(
                elo_score=sample_leaderboard.elo_score,
                vote_count=sample_leaderboard.vote_count,
                win_count=sample_leaderboard.win_count,
                loss_count=sample_leaderboard.loss_count,
                tie_count=sample_leaderboard.tie_count,
                win_rate=win_rate,
                last_updated=sample_leaderboard.last_updated.isoformat()
                if sample_leaderboard.last_updated
                else None,
            )
        else:
            logger.info(
                "No matching leaderboard entry found with the specific criteria"
            )

            # If we have a different test set in the leaderboard entries, use that instead
            if all_sample_entries:
                logger.info("Using the first available entry as a fallback")
                entry = all_sample_entries[0]
                win_rate = (
                    entry.win_count / entry.vote_count if entry.vote_count > 0 else 0
                )
                sample_stats = SampleStatsResponse(
                    elo_score=entry.elo_score,
                    vote_count=entry.vote_count,
                    win_count=entry.win_count,
                    loss_count=entry.loss_count,
                    tie_count=entry.tie_count,
                    win_rate=win_rate,
                    last_updated=entry.last_updated.isoformat()
                    if entry.last_updated
                    else None,
                )

    # Get prompt tags
    prompt_tags = [
        TagResponse(id=tag.external_id, name=tag.name) for tag in sample.run.prompt.tags
    ]

    # Create prompt response
    prompt_response = PromptResponse(
        id=sample.run.prompt.external_id,
        name=sample.run.prompt.name,
        build_specification=sample.run.prompt.build_specification,
        tags=prompt_tags,
    )

    # Create the run info response
    run_info = RunInfoResponse(
        model=ModelResponse(
            id=sample.run.model.external_id,
            name=sample.run.model.name,
            slug=sample.run.model.slug,
        ),
        prompt=prompt_response,
        template_name=sample.run.template.name,
    )

    # Create and return the sample response
    return SampleResponse(
        id=sample.external_id,
        created=sample.created,
        result_inspiration_text=sample.result_inspiration_text,
        result_description_text=sample.result_description_text,
        result_code_text=sample.result_code_text,
        is_complete=sample.is_complete,
        test_set_id=sample.test_set.external_id if sample.test_set else None,
        experimental_state=sample.experimental_state.name
        if sample.experimental_state
        else None,
        approval_state=sample.approval_state.name if sample.approval_state else None,
        run=run_info,
        artifacts=artifacts,
        stats=sample_stats,
    )
