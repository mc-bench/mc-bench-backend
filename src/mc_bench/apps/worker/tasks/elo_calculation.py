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
    db, prompt_id, model_id, metric_id, test_set_id, tag_id=None
):
    """Get or create a prompt leaderboard entry.

    This tracks how well each prompt performs for a specific model.
    """
    entry = db.execute(
        select(PromptLeaderboard).where(
            PromptLeaderboard.prompt_id == prompt_id,
            PromptLeaderboard.model_id == model_id,
            PromptLeaderboard.metric_id == metric_id,
            PromptLeaderboard.test_set_id == test_set_id,
            PromptLeaderboard.tag_id == tag_id,
        )
    ).scalar_one_or_none()

    if entry is None:
        entry = PromptLeaderboard(
            prompt_id=prompt_id,
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
    """Process a single comparison to update ELO scores.

    Simplified to handle only binary comparisons (one winner, one loser) or ties.
    """
    # Get the comparison
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

    # SIMPLIFIED: Ensure we have either 2 different ranks or 1 rank with multiple samples
    if len(sorted_ranks) > 2:
        logger.warning(
            f"Simplified ELO calculation only supports binary (win/lose) or tie comparisons. Skipping complex comparison {comparison_id}"
        )
        return

    # Fetch samples data and prepare for ELO calculation
    sample_data = {}
    for rank in sorted_ranks:
        for sample_id in samples_by_rank[rank]:
            sample = db.scalar(select(Sample).where(Sample.id == sample_id))
            if not sample:
                continue

            # Fetch prompt tags
            prompt_id = sample.run.prompt_id
            prompt_tag_query = text("""
                SELECT pt.tag_id 
                FROM specification.prompt_tag pt
                WHERE pt.prompt_id = :prompt_id
            """).bindparams(prompt_id=prompt_id)
            tag_ids = db.execute(prompt_tag_query).scalars().all()

            sample_data[sample_id] = {
                "model_id": sample.run.model_id,
                "prompt_id": prompt_id,
                "rank": rank,
                "tag_ids": tag_ids,
            }

    # If we have two different ranks, it's a win/loss situation
    is_tie = len(sorted_ranks) == 1

    # Setup leaderboard entries
    model_entries = {}  # (model_id, metric_id, test_set_id, tag_id) -> entry
    prompt_entries = {}  # (prompt_id, metric_id, test_set_id, tag_id) -> entry
    sample_entries = {}  # (sample_id, metric_id, test_set_id) -> entry

    # Get sample leaderboard entries
    for sample_id in sample_data.keys():
        sample_key = (sample_id, comparison.metric_id, comparison.test_set_id)
        sample_entries[sample_key] = get_or_create_sample_leaderboard(
            db, sample_id, comparison.metric_id, comparison.test_set_id
        )

    # Get model leaderboard entries (both global and tag-specific)
    for sample_id, info in sample_data.items():
        model_id = info["model_id"]

        # Global model entry (no tag)
        model_key = (model_id, comparison.metric_id, comparison.test_set_id, None)
        if model_key not in model_entries:
            model_entries[model_key] = get_or_create_model_leaderboard(
                db, model_id, comparison.metric_id, comparison.test_set_id, None
            )

        # Tag-specific model entries
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

    # Get prompt leaderboard entries (both global and tag-specific)
    for sample_id, info in sample_data.items():
        prompt_id = info["prompt_id"]

        # Global prompt entry (no tag)
        model_id = info["model_id"]
        prompt_key = (
            prompt_id,
            model_id,
            comparison.metric_id,
            comparison.test_set_id,
            None,
        )
        if prompt_key not in prompt_entries:
            prompt_entries[prompt_key] = get_or_create_prompt_leaderboard(
                db,
                prompt_id,
                model_id,
                comparison.metric_id,
                comparison.test_set_id,
                None,
            )

        # Tag-specific prompt entries
        for tag_id in info["tag_ids"]:
            tag_prompt_key = (
                prompt_id,
                model_id,
                comparison.metric_id,
                comparison.test_set_id,
                tag_id,
            )
            if tag_prompt_key not in prompt_entries:
                prompt_entries[tag_prompt_key] = get_or_create_prompt_leaderboard(
                    db,
                    prompt_id,
                    model_id,
                    comparison.metric_id,
                    comparison.test_set_id,
                    tag_id,
                )

    # SIMPLIFIED PROCESSING OF WIN/LOSS OR TIE

    # Handle tie case
    if is_tie:
        # Get the samples that tied (all samples have the same rank)
        tied_samples = list(sample_data.keys())

        # Process each pair of tied samples
        for i, sample_a_id in enumerate(tied_samples):
            for sample_b_id in tied_samples[i + 1 :]:
                # Skip if either sample is missing data
                if sample_a_id not in sample_data or sample_b_id not in sample_data:
                    continue

                # Get sample data
                sample_a = sample_data[sample_a_id]
                sample_b = sample_data[sample_b_id]

                # SAMPLE ELO UPDATE - TIE
                sample_a_key = (
                    sample_a_id,
                    comparison.metric_id,
                    comparison.test_set_id,
                )
                sample_b_key = (
                    sample_b_id,
                    comparison.metric_id,
                    comparison.test_set_id,
                )

                # Update vote count
                sample_entries[sample_a_key].vote_count += 1
                sample_entries[sample_b_key].vote_count += 1

                # Update tie count
                sample_entries[sample_a_key].tie_count += 1
                sample_entries[sample_b_key].tie_count += 1

                # Calculate ELO
                sample_a_rating = sample_entries[sample_a_key].elo_score
                sample_b_rating = sample_entries[sample_b_key].elo_score

                sample_a_expected = expected_score(sample_a_rating, sample_b_rating)
                sample_b_expected = expected_score(sample_b_rating, sample_a_rating)

                # Tie scores
                sample_a_actual = 0.5
                sample_b_actual = 0.5

                # Update ELO scores
                sample_a_new_rating = update_elo(
                    sample_a_rating,
                    sample_a_expected,
                    sample_a_actual,
                    settings.ELO_K_FACTOR,
                    settings.ELO_MIN_SCORE,
                )
                sample_b_new_rating = update_elo(
                    sample_b_rating,
                    sample_b_expected,
                    sample_b_actual,
                    settings.ELO_K_FACTOR,
                    settings.ELO_MIN_SCORE,
                )

                sample_entries[sample_a_key].elo_score = sample_a_new_rating
                sample_entries[sample_b_key].elo_score = sample_b_new_rating

                # MODEL ELO UPDATE - TIE
                model_a_id = sample_a["model_id"]
                model_b_id = sample_b["model_id"]

                # Update global model entries (no tag)
                model_a_key = (
                    model_a_id,
                    comparison.metric_id,
                    comparison.test_set_id,
                    None,
                )
                model_b_key = (
                    model_b_id,
                    comparison.metric_id,
                    comparison.test_set_id,
                    None,
                )

                # Update vote count
                model_entries[model_a_key].vote_count += 1
                model_entries[model_b_key].vote_count += 1

                # Update tie count
                model_entries[model_a_key].tie_count += 1
                model_entries[model_b_key].tie_count += 1

                # Calculate ELO
                model_a_rating = model_entries[model_a_key].elo_score
                model_b_rating = model_entries[model_b_key].elo_score

                model_a_expected = expected_score(model_a_rating, model_b_rating)
                model_b_expected = expected_score(model_b_rating, model_a_rating)

                # Tie scores
                model_a_actual = 0.5
                model_b_actual = 0.5

                # Update ELO scores
                model_a_new_rating = update_elo(
                    model_a_rating,
                    model_a_expected,
                    model_a_actual,
                    settings.ELO_K_FACTOR,
                    settings.ELO_MIN_SCORE,
                )
                model_b_new_rating = update_elo(
                    model_b_rating,
                    model_b_expected,
                    model_b_actual,
                    settings.ELO_K_FACTOR,
                    settings.ELO_MIN_SCORE,
                )

                model_entries[model_a_key].elo_score = model_a_new_rating
                model_entries[model_b_key].elo_score = model_b_new_rating

                # PROMPT ELO UPDATE - TIE
                prompt_a_id = sample_a["prompt_id"]
                prompt_b_id = sample_b["prompt_id"]

                # Update global prompt entries (no tag)
                # Include model_id in the key
                prompt_a_key = (
                    prompt_a_id,
                    model_a_id,
                    comparison.metric_id,
                    comparison.test_set_id,
                    None,
                )
                prompt_b_key = (
                    prompt_b_id,
                    model_b_id,
                    comparison.metric_id,
                    comparison.test_set_id,
                    None,
                )

                # Update vote count
                prompt_entries[prompt_a_key].vote_count += 1
                prompt_entries[prompt_b_key].vote_count += 1

                # Update tie count
                prompt_entries[prompt_a_key].tie_count += 1
                prompt_entries[prompt_b_key].tie_count += 1

                # Calculate ELO
                prompt_a_rating = prompt_entries[prompt_a_key].elo_score
                prompt_b_rating = prompt_entries[prompt_b_key].elo_score

                prompt_a_expected = expected_score(prompt_a_rating, prompt_b_rating)
                prompt_b_expected = expected_score(prompt_b_rating, prompt_a_rating)

                # Tie scores
                prompt_a_actual = 0.5
                prompt_b_actual = 0.5

                # Update ELO scores
                prompt_a_new_rating = update_elo(
                    prompt_a_rating,
                    prompt_a_expected,
                    prompt_a_actual,
                    settings.ELO_K_FACTOR,
                    settings.ELO_MIN_SCORE,
                )
                prompt_b_new_rating = update_elo(
                    prompt_b_rating,
                    prompt_b_expected,
                    prompt_b_actual,
                    settings.ELO_K_FACTOR,
                    settings.ELO_MIN_SCORE,
                )

                prompt_entries[prompt_a_key].elo_score = prompt_a_new_rating
                prompt_entries[prompt_b_key].elo_score = prompt_b_new_rating

                # Update tag-specific entries
                # Get the intersection of tags for both samples
                tags_a = set(sample_a["tag_ids"])
                tags_b = set(sample_b["tag_ids"])
                common_tags = tags_a.intersection(tags_b)

                for tag_id in common_tags:
                    # MODEL TAG UPDATE
                    tag_model_a_key = (
                        model_a_id,
                        comparison.metric_id,
                        comparison.test_set_id,
                        tag_id,
                    )
                    tag_model_b_key = (
                        model_b_id,
                        comparison.metric_id,
                        comparison.test_set_id,
                        tag_id,
                    )

                    # Update vote count
                    model_entries[tag_model_a_key].vote_count += 1
                    model_entries[tag_model_b_key].vote_count += 1

                    # Update tie count
                    model_entries[tag_model_a_key].tie_count += 1
                    model_entries[tag_model_b_key].tie_count += 1

                    # Calculate ELO
                    tag_model_a_rating = model_entries[tag_model_a_key].elo_score
                    tag_model_b_rating = model_entries[tag_model_b_key].elo_score

                    tag_model_a_expected = expected_score(
                        tag_model_a_rating, tag_model_b_rating
                    )
                    tag_model_b_expected = expected_score(
                        tag_model_b_rating, tag_model_a_rating
                    )

                    # Update ELO scores
                    tag_model_a_new_rating = update_elo(
                        tag_model_a_rating,
                        tag_model_a_expected,
                        0.5,  # tie
                        settings.ELO_K_FACTOR,
                        settings.ELO_MIN_SCORE,
                    )
                    tag_model_b_new_rating = update_elo(
                        tag_model_b_rating,
                        tag_model_b_expected,
                        0.5,  # tie
                        settings.ELO_K_FACTOR,
                        settings.ELO_MIN_SCORE,
                    )

                    model_entries[tag_model_a_key].elo_score = tag_model_a_new_rating
                    model_entries[tag_model_b_key].elo_score = tag_model_b_new_rating

                    # PROMPT TAG UPDATE
                    tag_prompt_a_key = (
                        prompt_a_id,
                        model_a_id,
                        comparison.metric_id,
                        comparison.test_set_id,
                        tag_id,
                    )
                    tag_prompt_b_key = (
                        prompt_b_id,
                        model_b_id,
                        comparison.metric_id,
                        comparison.test_set_id,
                        tag_id,
                    )

                    # Update vote count
                    prompt_entries[tag_prompt_a_key].vote_count += 1
                    prompt_entries[tag_prompt_b_key].vote_count += 1

                    # Update tie count
                    prompt_entries[tag_prompt_a_key].tie_count += 1
                    prompt_entries[tag_prompt_b_key].tie_count += 1

                    # Calculate ELO
                    tag_prompt_a_rating = prompt_entries[tag_prompt_a_key].elo_score
                    tag_prompt_b_rating = prompt_entries[tag_prompt_b_key].elo_score

                    tag_prompt_a_expected = expected_score(
                        tag_prompt_a_rating, tag_prompt_b_rating
                    )
                    tag_prompt_b_expected = expected_score(
                        tag_prompt_b_rating, tag_prompt_a_rating
                    )

                    # Update ELO scores
                    tag_prompt_a_new_rating = update_elo(
                        tag_prompt_a_rating,
                        tag_prompt_a_expected,
                        0.5,  # tie
                        settings.ELO_K_FACTOR,
                        settings.ELO_MIN_SCORE,
                    )
                    tag_prompt_b_new_rating = update_elo(
                        tag_prompt_b_rating,
                        tag_prompt_b_expected,
                        0.5,  # tie
                        settings.ELO_K_FACTOR,
                        settings.ELO_MIN_SCORE,
                    )

                    prompt_entries[tag_prompt_a_key].elo_score = tag_prompt_a_new_rating
                    prompt_entries[tag_prompt_b_key].elo_score = tag_prompt_b_new_rating

    else:
        # Win/loss case - we have two different ranks
        # First rank has the winners, second rank has the losers
        winners = samples_by_rank[sorted_ranks[0]]
        losers = samples_by_rank[sorted_ranks[1]]

        # Process all winner/loser pairs
        for winner_id in winners:
            for loser_id in losers:
                # Skip if either sample is missing data
                if winner_id not in sample_data or loser_id not in sample_data:
                    continue

                # Get sample data
                winner = sample_data[winner_id]
                loser = sample_data[loser_id]

                # SAMPLE ELO UPDATE - WIN/LOSS
                winner_key = (winner_id, comparison.metric_id, comparison.test_set_id)
                loser_key = (loser_id, comparison.metric_id, comparison.test_set_id)

                # Update vote count
                sample_entries[winner_key].vote_count += 1
                sample_entries[loser_key].vote_count += 1

                # Update win/loss count
                sample_entries[winner_key].win_count += 1
                sample_entries[loser_key].loss_count += 1

                # Calculate ELO
                winner_rating = sample_entries[winner_key].elo_score
                loser_rating = sample_entries[loser_key].elo_score

                winner_expected = expected_score(winner_rating, loser_rating)
                loser_expected = expected_score(loser_rating, winner_rating)

                # Win/loss scores
                winner_actual = 1.0
                loser_actual = 0.0

                # Update ELO scores
                winner_new_rating = update_elo(
                    winner_rating,
                    winner_expected,
                    winner_actual,
                    settings.ELO_K_FACTOR,
                    settings.ELO_MIN_SCORE,
                )
                loser_new_rating = update_elo(
                    loser_rating,
                    loser_expected,
                    loser_actual,
                    settings.ELO_K_FACTOR,
                    settings.ELO_MIN_SCORE,
                )

                sample_entries[winner_key].elo_score = winner_new_rating
                sample_entries[loser_key].elo_score = loser_new_rating

                # MODEL ELO UPDATE - WIN/LOSS
                winner_model_id = winner["model_id"]
                loser_model_id = loser["model_id"]

                # Update global model entries (no tag)
                winner_model_key = (
                    winner_model_id,
                    comparison.metric_id,
                    comparison.test_set_id,
                    None,
                )
                loser_model_key = (
                    loser_model_id,
                    comparison.metric_id,
                    comparison.test_set_id,
                    None,
                )

                # Update vote count
                model_entries[winner_model_key].vote_count += 1
                model_entries[loser_model_key].vote_count += 1

                # Update win/loss count
                model_entries[winner_model_key].win_count += 1
                model_entries[loser_model_key].loss_count += 1

                # Calculate ELO
                winner_model_rating = model_entries[winner_model_key].elo_score
                loser_model_rating = model_entries[loser_model_key].elo_score

                winner_model_expected = expected_score(
                    winner_model_rating, loser_model_rating
                )
                loser_model_expected = expected_score(
                    loser_model_rating, winner_model_rating
                )

                # Win/loss scores
                winner_model_actual = 1.0
                loser_model_actual = 0.0

                # Update ELO scores
                winner_model_new_rating = update_elo(
                    winner_model_rating,
                    winner_model_expected,
                    winner_model_actual,
                    settings.ELO_K_FACTOR,
                    settings.ELO_MIN_SCORE,
                )
                loser_model_new_rating = update_elo(
                    loser_model_rating,
                    loser_model_expected,
                    loser_model_actual,
                    settings.ELO_K_FACTOR,
                    settings.ELO_MIN_SCORE,
                )

                model_entries[winner_model_key].elo_score = winner_model_new_rating
                model_entries[loser_model_key].elo_score = loser_model_new_rating

                # PROMPT ELO UPDATE - WIN/LOSS
                winner_prompt_id = winner["prompt_id"]
                loser_prompt_id = loser["prompt_id"]

                # Update global prompt entries (no tag)
                winner_prompt_key = (
                    winner_prompt_id,
                    winner_model_id,
                    comparison.metric_id,
                    comparison.test_set_id,
                    None,
                )
                loser_prompt_key = (
                    loser_prompt_id,
                    loser_model_id,
                    comparison.metric_id,
                    comparison.test_set_id,
                    None,
                )

                # Update vote count
                prompt_entries[winner_prompt_key].vote_count += 1
                prompt_entries[loser_prompt_key].vote_count += 1

                # Update win/loss count
                prompt_entries[winner_prompt_key].win_count += 1
                prompt_entries[loser_prompt_key].loss_count += 1

                # Calculate ELO
                winner_prompt_rating = prompt_entries[winner_prompt_key].elo_score
                loser_prompt_rating = prompt_entries[loser_prompt_key].elo_score

                winner_prompt_expected = expected_score(
                    winner_prompt_rating, loser_prompt_rating
                )
                loser_prompt_expected = expected_score(
                    loser_prompt_rating, winner_prompt_rating
                )

                # Win/loss scores
                winner_prompt_actual = 1.0
                loser_prompt_actual = 0.0

                # Update ELO scores
                winner_prompt_new_rating = update_elo(
                    winner_prompt_rating,
                    winner_prompt_expected,
                    winner_prompt_actual,
                    settings.ELO_K_FACTOR,
                    settings.ELO_MIN_SCORE,
                )
                loser_prompt_new_rating = update_elo(
                    loser_prompt_rating,
                    loser_prompt_expected,
                    loser_prompt_actual,
                    settings.ELO_K_FACTOR,
                    settings.ELO_MIN_SCORE,
                )

                prompt_entries[winner_prompt_key].elo_score = winner_prompt_new_rating
                prompt_entries[loser_prompt_key].elo_score = loser_prompt_new_rating

                # Update tag-specific entries
                # Get the intersection of tags for both samples
                winner_tags = set(winner["tag_ids"])
                loser_tags = set(loser["tag_ids"])
                common_tags = winner_tags.intersection(loser_tags)

                for tag_id in common_tags:
                    # MODEL TAG UPDATE
                    tag_winner_model_key = (
                        winner_model_id,
                        comparison.metric_id,
                        comparison.test_set_id,
                        tag_id,
                    )
                    tag_loser_model_key = (
                        loser_model_id,
                        comparison.metric_id,
                        comparison.test_set_id,
                        tag_id,
                    )

                    # Update vote count
                    model_entries[tag_winner_model_key].vote_count += 1
                    model_entries[tag_loser_model_key].vote_count += 1

                    # Update win/loss count
                    model_entries[tag_winner_model_key].win_count += 1
                    model_entries[tag_loser_model_key].loss_count += 1

                    # Calculate ELO
                    tag_winner_model_rating = model_entries[
                        tag_winner_model_key
                    ].elo_score
                    tag_loser_model_rating = model_entries[
                        tag_loser_model_key
                    ].elo_score

                    tag_winner_model_expected = expected_score(
                        tag_winner_model_rating, tag_loser_model_rating
                    )
                    tag_loser_model_expected = expected_score(
                        tag_loser_model_rating, tag_winner_model_rating
                    )

                    # Update ELO scores
                    tag_winner_model_new_rating = update_elo(
                        tag_winner_model_rating,
                        tag_winner_model_expected,
                        1.0,  # win
                        settings.ELO_K_FACTOR,
                        settings.ELO_MIN_SCORE,
                    )
                    tag_loser_model_new_rating = update_elo(
                        tag_loser_model_rating,
                        tag_loser_model_expected,
                        0.0,  # loss
                        settings.ELO_K_FACTOR,
                        settings.ELO_MIN_SCORE,
                    )

                    model_entries[
                        tag_winner_model_key
                    ].elo_score = tag_winner_model_new_rating
                    model_entries[
                        tag_loser_model_key
                    ].elo_score = tag_loser_model_new_rating

                    # PROMPT TAG UPDATE
                    tag_winner_prompt_key = (
                        winner_prompt_id,
                        winner_model_id,
                        comparison.metric_id,
                        comparison.test_set_id,
                        tag_id,
                    )
                    tag_loser_prompt_key = (
                        loser_prompt_id,
                        loser_model_id,
                        comparison.metric_id,
                        comparison.test_set_id,
                        tag_id,
                    )

                    # Update vote count
                    prompt_entries[tag_winner_prompt_key].vote_count += 1
                    prompt_entries[tag_loser_prompt_key].vote_count += 1

                    # Update win/loss count
                    prompt_entries[tag_winner_prompt_key].win_count += 1
                    prompt_entries[tag_loser_prompt_key].loss_count += 1

                    # Calculate ELO
                    tag_winner_prompt_rating = prompt_entries[
                        tag_winner_prompt_key
                    ].elo_score
                    tag_loser_prompt_rating = prompt_entries[
                        tag_loser_prompt_key
                    ].elo_score

                    tag_winner_prompt_expected = expected_score(
                        tag_winner_prompt_rating, tag_loser_prompt_rating
                    )
                    tag_loser_prompt_expected = expected_score(
                        tag_loser_prompt_rating, tag_winner_prompt_rating
                    )

                    # Update ELO scores
                    tag_winner_prompt_new_rating = update_elo(
                        tag_winner_prompt_rating,
                        tag_winner_prompt_expected,
                        1.0,  # win
                        settings.ELO_K_FACTOR,
                        settings.ELO_MIN_SCORE,
                    )
                    tag_loser_prompt_new_rating = update_elo(
                        tag_loser_prompt_rating,
                        tag_loser_prompt_expected,
                        0.0,  # loss
                        settings.ELO_K_FACTOR,
                        settings.ELO_MIN_SCORE,
                    )

                    prompt_entries[
                        tag_winner_prompt_key
                    ].elo_score = tag_winner_prompt_new_rating
                    prompt_entries[
                        tag_loser_prompt_key
                    ].elo_score = tag_loser_prompt_new_rating

    # Update the last_updated timestamp for all modified entries
    now = datetime.datetime.now()

    for entry in model_entries.values():
        entry.last_updated = now

    for entry in prompt_entries.values():
        entry.last_updated = now

    for entry in sample_entries.values():
        entry.last_updated = now

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
