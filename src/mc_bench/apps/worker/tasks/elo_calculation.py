import datetime
from collections import defaultdict

from sqlalchemy import select, text

from mc_bench.models.comparison import (
    Comparison,
    ComparisonRank,
    ModelLeaderboard,
    ProcessedComparison,
    PromptLeaderboard,
    SampleLeaderboard,
)
from mc_bench.models.run import Sample
from mc_bench.util.elo import expected_score, update_elo
from mc_bench.util.logging import get_logger
from mc_bench.util.postgres import managed_session
from mc_bench.util.redis import RedisDatabase, get_redis_client

from ..app import app
from ..config import settings

logger = get_logger(__name__)


def get_or_create_model_leaderboard(db, model_id, metric_id, test_set_id, tag_id=None):
    """Get or create a model leaderboard entry."""
    entry = db.execute(
        select(ModelLeaderboard).where(
            ModelLeaderboard.model_id == model_id,
            ModelLeaderboard.metric_id == metric_id,
            ModelLeaderboard.test_set_id == test_set_id,
            ModelLeaderboard.tag_id == tag_id,
        )
    ).scalar_one_or_none()

    if entry is None:
        entry = ModelLeaderboard(
            model_id=model_id,
            metric_id=metric_id,
            test_set_id=test_set_id,
            tag_id=tag_id,
            elo_score=settings.ELO_DEFAULT_SCORE,
            vote_count=0,
            win_count=0,
            loss_count=0,
            tie_count=0,
        )
        db.add(entry)
        db.flush()

    return entry


def get_or_create_prompt_leaderboard(
    db, prompt_id, metric_id, test_set_id, tag_id=None
):
    """Get or create a prompt leaderboard entry."""
    entry = db.execute(
        select(PromptLeaderboard).where(
            PromptLeaderboard.prompt_id == prompt_id,
            PromptLeaderboard.metric_id == metric_id,
            PromptLeaderboard.test_set_id == test_set_id,
            PromptLeaderboard.tag_id == tag_id,
        )
    ).scalar_one_or_none()

    if entry is None:
        entry = PromptLeaderboard(
            prompt_id=prompt_id,
            metric_id=metric_id,
            test_set_id=test_set_id,
            tag_id=tag_id,
            elo_score=settings.ELO_DEFAULT_SCORE,
            vote_count=0,
            win_count=0,
            loss_count=0,
            tie_count=0,
        )
        db.add(entry)
        db.flush()

    return entry


def get_or_create_sample_leaderboard(db, sample_id, metric_id, test_set_id):
    """Get or create a sample leaderboard entry."""
    entry = db.execute(
        select(SampleLeaderboard).where(
            SampleLeaderboard.sample_id == sample_id,
            SampleLeaderboard.metric_id == metric_id,
            SampleLeaderboard.test_set_id == test_set_id,
        )
    ).scalar_one_or_none()

    if entry is None:
        entry = SampleLeaderboard(
            sample_id=sample_id,
            metric_id=metric_id,
            test_set_id=test_set_id,
            elo_score=settings.ELO_DEFAULT_SCORE,
            vote_count=0,
            win_count=0,
            loss_count=0,
            tie_count=0,
        )
        db.add(entry)
        db.flush()

    return entry


def process_comparison_for_elo(db, comparison_id):
    """Process a single comparison to update ELO scores."""
    # Get the comparison with all its ranks
    comparison = db.scalar(select(Comparison).where(Comparison.id == comparison_id))
    if not comparison:
        logger.warning(f"Comparison {comparison_id} not found")
        return

    # Get all the ranks for this comparison
    ranks = (
        db.execute(
            select(ComparisonRank)
            .where(ComparisonRank.comparison_id == comparison_id)
            .order_by(ComparisonRank.rank)
        )
        .scalars()
        .all()
    )

    if not ranks or len(ranks) < 2:
        logger.warning(f"Comparison {comparison_id} has fewer than 2 ranks")
        return

    # Group samples by rank to handle ties
    samples_by_rank = defaultdict(list)
    for rank_entry in ranks:
        samples_by_rank[rank_entry.rank].append(rank_entry.sample_id)

    # Get all unique ranks sorted
    sorted_ranks = sorted(samples_by_rank.keys())

    # Get info about the samples and their associated tags
    sample_info = {}
    prompt_tags = {}  # Cache to avoid duplicate queries

    for rank_entry in ranks:
        sample = db.scalar(select(Sample).where(Sample.id == rank_entry.sample_id))
        if not sample:
            continue

        # Get or cache the prompt's tags
        prompt_id = sample.run.prompt_id
        if prompt_id not in prompt_tags:
            # Get all tags for this prompt
            prompt_tag_query = text("""
                SELECT pt.tag_id 
                FROM specification.prompt_tag pt
                WHERE pt.prompt_id = :prompt_id
            """).bindparams(prompt_id=prompt_id)

            tag_ids = db.execute(prompt_tag_query).scalars().all()
            prompt_tags[prompt_id] = tag_ids

        sample_info[rank_entry.sample_id] = {
            "model_id": sample.run.model_id,
            "test_set_id": comparison.test_set_id,
            "sample_id": sample.id,
            "rank": rank_entry.rank,
            "prompt_id": prompt_id,
            "tag_ids": prompt_tags[prompt_id],
        }

    # Dictionary to track leaderboard entries to update
    model_entries = {}
    prompt_entries = {}
    sample_entries = {}

    # Get sample, model, and prompt leaderboard entries for each sample
    for sample_id, info in sample_info.items():
        model_id = info["model_id"]
        prompt_id = info["prompt_id"]

        # First, get or create the global model leaderboard entry (tag_id=None)
        model_key = (model_id, comparison.metric_id, comparison.test_set_id, None)
        if model_key not in model_entries:
            model_entries[model_key] = get_or_create_model_leaderboard(
                db, model_id, comparison.metric_id, comparison.test_set_id, None
            )

        # Then get or create model entries for each tag
        for tag_id in info["tag_ids"]:
            tag_model_key = (
                model_id,
                comparison.metric_id,
                comparison.test_set_id,
                tag_id,
            )
            if tag_model_key not in model_entries:
                model_entries[tag_model_key] = get_or_create_model_leaderboard(
                    db, model_id, comparison.metric_id, comparison.test_set_id, tag_id
                )

        # First, get or create the global prompt leaderboard entry (tag_id=None)
        prompt_key = (prompt_id, comparison.metric_id, comparison.test_set_id, None)
        if prompt_key not in prompt_entries:
            prompt_entries[prompt_key] = get_or_create_prompt_leaderboard(
                db, prompt_id, comparison.metric_id, comparison.test_set_id, None
            )

        # Then get or create prompt entries for each tag
        for tag_id in info["tag_ids"]:
            tag_prompt_key = (
                prompt_id,
                comparison.metric_id,
                comparison.test_set_id,
                tag_id,
            )
            if tag_prompt_key not in prompt_entries:
                prompt_entries[tag_prompt_key] = get_or_create_prompt_leaderboard(
                    db, prompt_id, comparison.metric_id, comparison.test_set_id, tag_id
                )

        # Get or create sample leaderboard entry
        sample_key = (sample_id, comparison.metric_id, comparison.test_set_id)
        if sample_key not in sample_entries:
            sample_entries[sample_key] = get_or_create_sample_leaderboard(
                db, sample_id, comparison.metric_id, comparison.test_set_id
            )

    # Calculate new ELO scores based on pairwise comparisons
    model_elo_updates = defaultdict(lambda: {"score": 0, "count": 0})
    prompt_elo_updates = defaultdict(lambda: {"score": 0, "count": 0})
    sample_elo_updates = defaultdict(lambda: {"score": 0, "count": 0})

    # Update vote counts for all entries involved
    for model_key, entry in model_entries.items():
        entry.vote_count += 1

    for prompt_key, entry in prompt_entries.items():
        entry.vote_count += 1

    for sample_key, entry in sample_entries.items():
        entry.vote_count += 1

    # Process each pair of ranks (1 vs 2, 1 vs 3, 2 vs 3, etc.)
    # This handles all pairwise comparisons
    for i, rank_i in enumerate(sorted_ranks):
        for rank_j in sorted_ranks[i + 1 :]:
            # For all samples with rank_i vs all samples with rank_j
            for sample_i_id in samples_by_rank[rank_i]:
                for sample_j_id in samples_by_rank[rank_j]:
                    if sample_i_id not in sample_info or sample_j_id not in sample_info:
                        continue

                    # Get model and prompt information
                    model_i_id = sample_info[sample_i_id]["model_id"]
                    model_j_id = sample_info[sample_j_id]["model_id"]
                    prompt_i_id = sample_info[sample_i_id]["prompt_id"]
                    prompt_j_id = sample_info[sample_j_id]["prompt_id"]

                    # Define a function to process model ELO updates for a specific model pair and tag
                    def process_model_elo(model_i_id, model_j_id, tag_id=None):
                        # Model keys for this tag (or global if tag_id is None)
                        model_i_key = (
                            model_i_id,
                            comparison.metric_id,
                            comparison.test_set_id,
                            tag_id,
                        )
                        model_j_key = (
                            model_j_id,
                            comparison.metric_id,
                            comparison.test_set_id,
                            tag_id,
                        )

                        # If we don't have entries for these keys (could happen for tag-specific entries),
                        # create them now
                        if model_i_key not in model_entries:
                            model_entries[model_i_key] = (
                                get_or_create_model_leaderboard(
                                    db,
                                    model_i_id,
                                    comparison.metric_id,
                                    comparison.test_set_id,
                                    tag_id,
                                )
                            )
                            model_entries[model_i_key].vote_count += 1

                        if model_j_key not in model_entries:
                            model_entries[model_j_key] = (
                                get_or_create_model_leaderboard(
                                    db,
                                    model_j_id,
                                    comparison.metric_id,
                                    comparison.test_set_id,
                                    tag_id,
                                )
                            )
                            model_entries[model_j_key].vote_count += 1

                        # Get current ELO ratings for this tag
                        model_i_rating = model_entries[model_i_key].elo_score
                        model_j_rating = model_entries[model_j_key].elo_score

                        # Expected scores
                        model_i_expected = expected_score(
                            model_i_rating, model_j_rating
                        )
                        model_j_expected = expected_score(
                            model_j_rating, model_i_rating
                        )

                        # Actual scores determined by rank
                        if rank_i < rank_j:  # i wins
                            model_i_actual = 1.0
                            model_j_actual = 0.0

                            # Update win/loss counts
                            model_entries[model_i_key].win_count += 1
                            model_entries[model_j_key].loss_count += 1
                        elif rank_i > rank_j:  # j wins
                            model_i_actual = 0.0
                            model_j_actual = 1.0

                            # Update win/loss counts
                            model_entries[model_i_key].loss_count += 1
                            model_entries[model_j_key].win_count += 1
                        else:  # tie
                            model_i_actual = 0.5
                            model_j_actual = 0.5

                            # Update tie counts
                            model_entries[model_i_key].tie_count += 1
                            model_entries[model_j_key].tie_count += 1

                        # Calculate new ELO ratings
                        model_i_new_rating = update_elo(
                            model_i_rating,
                            model_i_expected,
                            model_i_actual,
                            settings.ELO_K_FACTOR,
                            settings.ELO_MIN_SCORE,
                        )
                        model_j_new_rating = update_elo(
                            model_j_rating,
                            model_j_expected,
                            model_j_actual,
                            settings.ELO_K_FACTOR,
                            settings.ELO_MIN_SCORE,
                        )

                        # Accumulate ELO updates
                        model_elo_updates[model_i_key]["score"] += model_i_new_rating
                        model_elo_updates[model_i_key]["count"] += 1
                        model_elo_updates[model_j_key]["score"] += model_j_new_rating
                        model_elo_updates[model_j_key]["count"] += 1

                    # Define a function to process prompt ELO updates for a specific prompt pair and tag
                    def process_prompt_elo(prompt_i_id, prompt_j_id, tag_id=None):
                        # Prompt keys for this tag (or global if tag_id is None)
                        prompt_i_key = (
                            prompt_i_id,
                            comparison.metric_id,
                            comparison.test_set_id,
                            tag_id,
                        )
                        prompt_j_key = (
                            prompt_j_id,
                            comparison.metric_id,
                            comparison.test_set_id,
                            tag_id,
                        )

                        # If we don't have entries for these keys (could happen for tag-specific entries),
                        # create them now
                        if prompt_i_key not in prompt_entries:
                            prompt_entries[prompt_i_key] = (
                                get_or_create_prompt_leaderboard(
                                    db,
                                    prompt_i_id,
                                    comparison.metric_id,
                                    comparison.test_set_id,
                                    tag_id,
                                )
                            )
                            prompt_entries[prompt_i_key].vote_count += 1

                        if prompt_j_key not in prompt_entries:
                            prompt_entries[prompt_j_key] = (
                                get_or_create_prompt_leaderboard(
                                    db,
                                    prompt_j_id,
                                    comparison.metric_id,
                                    comparison.test_set_id,
                                    tag_id,
                                )
                            )
                            prompt_entries[prompt_j_key].vote_count += 1

                        # Get current ELO ratings for this tag
                        prompt_i_rating = prompt_entries[prompt_i_key].elo_score
                        prompt_j_rating = prompt_entries[prompt_j_key].elo_score

                        # Expected scores
                        prompt_i_expected = expected_score(
                            prompt_i_rating, prompt_j_rating
                        )
                        prompt_j_expected = expected_score(
                            prompt_j_rating, prompt_i_rating
                        )

                        # Actual scores determined by rank
                        if rank_i < rank_j:  # i wins
                            prompt_i_actual = 1.0
                            prompt_j_actual = 0.0

                            # Update win/loss counts
                            prompt_entries[prompt_i_key].win_count += 1
                            prompt_entries[prompt_j_key].loss_count += 1
                        elif rank_i > rank_j:  # j wins
                            prompt_i_actual = 0.0
                            prompt_j_actual = 1.0

                            # Update win/loss counts
                            prompt_entries[prompt_i_key].loss_count += 1
                            prompt_entries[prompt_j_key].win_count += 1
                        else:  # tie
                            prompt_i_actual = 0.5
                            prompt_j_actual = 0.5

                            # Update tie counts
                            prompt_entries[prompt_i_key].tie_count += 1
                            prompt_entries[prompt_j_key].tie_count += 1

                        # Calculate new ELO ratings
                        prompt_i_new_rating = update_elo(
                            prompt_i_rating,
                            prompt_i_expected,
                            prompt_i_actual,
                            settings.ELO_K_FACTOR,
                            settings.ELO_MIN_SCORE,
                        )
                        prompt_j_new_rating = update_elo(
                            prompt_j_rating,
                            prompt_j_expected,
                            prompt_j_actual,
                            settings.ELO_K_FACTOR,
                            settings.ELO_MIN_SCORE,
                        )

                        # Accumulate ELO updates
                        prompt_elo_updates[prompt_i_key]["score"] += prompt_i_new_rating
                        prompt_elo_updates[prompt_i_key]["count"] += 1
                        prompt_elo_updates[prompt_j_key]["score"] += prompt_j_new_rating
                        prompt_elo_updates[prompt_j_key]["count"] += 1

                    # Process sample ELO updates
                    sample_i_key = (
                        sample_i_id,
                        comparison.metric_id,
                        comparison.test_set_id,
                    )
                    sample_j_key = (
                        sample_j_id,
                        comparison.metric_id,
                        comparison.test_set_id,
                    )

                    sample_i_rating = sample_entries[sample_i_key].elo_score
                    sample_j_rating = sample_entries[sample_j_key].elo_score

                    sample_i_expected = expected_score(sample_i_rating, sample_j_rating)
                    sample_j_expected = expected_score(sample_j_rating, sample_i_rating)

                    # Determine actual scores based on rank
                    if rank_i < rank_j:  # i wins
                        sample_i_actual = 1.0
                        sample_j_actual = 0.0

                        # Update win/loss counts
                        sample_entries[sample_i_key].win_count += 1
                        sample_entries[sample_j_key].loss_count += 1
                    elif rank_i > rank_j:  # j wins
                        sample_i_actual = 0.0
                        sample_j_actual = 1.0

                        # Update win/loss counts
                        sample_entries[sample_i_key].loss_count += 1
                        sample_entries[sample_j_key].win_count += 1
                    else:  # tie
                        sample_i_actual = 0.5
                        sample_j_actual = 0.5

                        # Update tie counts
                        sample_entries[sample_i_key].tie_count += 1
                        sample_entries[sample_j_key].tie_count += 1

                    # Calculate new sample ELO ratings
                    sample_i_new_rating = update_elo(
                        sample_i_rating,
                        sample_i_expected,
                        sample_i_actual,
                        settings.ELO_K_FACTOR,
                        settings.ELO_MIN_SCORE,
                    )
                    sample_j_new_rating = update_elo(
                        sample_j_rating,
                        sample_j_expected,
                        sample_j_actual,
                        settings.ELO_K_FACTOR,
                        settings.ELO_MIN_SCORE,
                    )

                    # Accumulate sample ELO updates
                    sample_elo_updates[sample_i_key]["score"] += sample_i_new_rating
                    sample_elo_updates[sample_i_key]["count"] += 1
                    sample_elo_updates[sample_j_key]["score"] += sample_j_new_rating
                    sample_elo_updates[sample_j_key]["count"] += 1

                    # First, process the global ELO updates (tag_id=None)
                    process_model_elo(model_i_id, model_j_id, None)
                    process_prompt_elo(prompt_i_id, prompt_j_id, None)

                    # Then process tag-specific ELO updates
                    # We need to find the intersection of tags from both samples
                    tag_ids_i = set(sample_info[sample_i_id]["tag_ids"])
                    tag_ids_j = set(sample_info[sample_j_id]["tag_ids"])

                    # Process shared tags
                    for tag_id in tag_ids_i.intersection(tag_ids_j):
                        process_model_elo(model_i_id, model_j_id, tag_id)
                        process_prompt_elo(prompt_i_id, prompt_j_id, tag_id)

    # Apply accumulated ELO updates (averaging all pairwise comparisons)
    now = datetime.datetime.now()
    for model_key, updates in model_elo_updates.items():
        if updates["count"] > 0:
            model_entries[model_key].elo_score = updates["score"] / updates["count"]
            model_entries[model_key].last_updated = now

    for prompt_key, updates in prompt_elo_updates.items():
        if updates["count"] > 0:
            prompt_entries[prompt_key].elo_score = updates["score"] / updates["count"]
            prompt_entries[prompt_key].last_updated = now

    for sample_key, updates in sample_elo_updates.items():
        if updates["count"] > 0:
            sample_entries[sample_key].elo_score = updates["score"] / updates["count"]
            sample_entries[sample_key].last_updated = now

    # Commit all changes
    db.commit()
    return True


# Use batch size from settings


@app.task(name="elo_calculation")
def elo_calculation():
    total_processed = 0
    total_errors = 0

    try:
        logger.info("Starting ELO calculation")

        while True:
            with managed_session() as db:
                # Lock all relevant tables at the beginning of the transaction
                logger.info("Acquiring locks on comparison and leaderboard tables")
                db.execute(
                    text("LOCK TABLE scoring.processed_comparison IN EXCLUSIVE MODE")
                )
                db.execute(
                    text("LOCK TABLE scoring.model_leaderboard IN EXCLUSIVE MODE")
                )
                db.execute(
                    text("LOCK TABLE scoring.prompt_leaderboard IN EXCLUSIVE MODE")
                )
                db.execute(
                    text("LOCK TABLE scoring.sample_leaderboard IN EXCLUSIVE MODE")
                )

                # Find comparisons that haven't been processed yet, limited by batch size
                # Join with comparison_rank to ensure we only process comparisons with at least 2 ranks
                # Use a left join with processed_comparison and filter where it's NULL
                batch_size = settings.ELO_BATCH_SIZE
                logger.info(
                    f"Finding unprocessed comparisons (batch size: {batch_size})"
                )

                unprocessed_query = text("""
                    SELECT cr.comparison_id, MIN(cr.created) as min_created
                    FROM scoring.comparison_rank cr
                    LEFT JOIN scoring.processed_comparison pc ON cr.comparison_id = pc.comparison_id
                    WHERE pc.id IS NULL
                    GROUP BY cr.comparison_id
                    HAVING COUNT(cr.id) >= 2
                    ORDER BY min_created ASC
                    LIMIT :batch_size
                """).bindparams(batch_size=batch_size)

                # Extract just the comparison_id column
                result = db.execute(unprocessed_query).all()
                unprocessed_comparison_ids = [row[0] for row in result]

                batch_size = len(unprocessed_comparison_ids)
                logger.info(f"Found {batch_size} unprocessed comparisons in this batch")

                # If no more unprocessed comparisons, break the loop
                if batch_size == 0:
                    logger.info("No more unprocessed comparisons found, exiting")
                    break

                batch_processed = 0
                batch_errors = 0

                for comparison_id in unprocessed_comparison_ids:
                    try:
                        # Process the comparison
                        process_comparison_for_elo(db, comparison_id)

                        # Mark as processed
                        db.add(ProcessedComparison(comparison_id=comparison_id))
                        db.commit()

                        batch_processed += 1
                        if batch_processed % 100 == 0:
                            logger.info(
                                f"Processed {batch_processed}/{batch_size} comparisons in current batch"
                            )

                    except Exception as e:
                        batch_errors += 1
                        logger.error(
                            f"Error processing comparison {comparison_id}: {e}"
                        )
                        db.rollback()  # Rollback on error

                logger.info(
                    f"Batch completed. Processed: {batch_processed}, Errors: {batch_errors}"
                )
                total_processed += batch_processed
                total_errors += batch_errors

        logger.info(
            f"All ELO calculations completed. Total processed: {total_processed}, Total errors: {total_errors}"
        )

    finally:
        redis = get_redis_client(RedisDatabase.COMPARISON)
        try:
            logger.info("Deleting elo calculation in progress key")
            redis.delete("elo_calculation_in_progress")
            logger.info("ELO calculation in progress key deleted")
        finally:
            redis.close()

    return {"processed": total_processed, "errors": total_errors}
