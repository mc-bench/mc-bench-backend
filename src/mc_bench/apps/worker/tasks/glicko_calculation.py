"""
Processes comparisons to update Glicko-2 ratings for models, prompts, and samples.

This module handles the backend processing of ratings when comparisons are submitted.
"""

import datetime
from collections import defaultdict

from sqlalchemy import select, text

from mc_bench.models.comparison import (
    Comparison,
    ComparisonRank, 
    ModelGlickoLeaderboard,
    ProcessedComparison,
)
from mc_bench.models.run import Sample
from mc_bench.util.glicko2 import GlickoRating, update_glicko2_rating
from mc_bench.util.logging import get_logger
from mc_bench.util.postgres import managed_session
from mc_bench.util.redis import RedisDatabase, get_redis_client

from ..app import app
from ..config import settings

logger = get_logger(__name__)


@app.task(name="glicko_calculation")
def glicko_calculation():
    """
    Process all unprocessed comparisons to update Glicko-2 ratings.
    
    This task:
    1. Finds all unprocessed comparisons
    2. Updates model and sample Glicko-2 ratings
    3. Marks comparisons as processed
    
    Returns:
        dict: Summary of processing results
    """
    logger.info("Starting Glicko-2 calculation")
    
    redis = get_redis_client(RedisDatabase.COMPARISON)
    
    # Check if already running
    if redis.get("glicko_calculation_in_progress"):
        logger.info("Glicko-2 calculation already in progress, exiting")
        return {"processed": 0, "errors": 0}
    
    # Set lock to prevent multiple calculations running simultaneously
    redis.setex("glicko_calculation_in_progress", 3600, "1")  # 1 hour timeout
    
    processed_count = 0
    error_count = 0
    
    try:
        with managed_session() as db:
            # Find unprocessed comparisons
            # We need to lock tables to prevent race conditions
            db.execute(
                text(
                    """
                    LOCK TABLE 
                    scoring.comparison, 
                    scoring.processed_comparison, 
                    scoring.model_glicko_leaderboard
                    IN SHARE ROW EXCLUSIVE MODE
                    """
                )
            )
            
            # Find comparisons that don't have a corresponding entry in processed_comparison
            unprocessed_query = select(Comparison).outerjoin(
                ProcessedComparison,
                Comparison.id == ProcessedComparison.comparison_id
            ).where(
                ProcessedComparison.id == None
            ).limit(1000)  # Process in batches
            
            unprocessed = db.scalars(unprocessed_query).all()
            
            logger.info(f"Found {len(unprocessed)} unprocessed comparisons for Glicko-2")
            
            # Process each comparison
            for comparison in unprocessed:
                try:
                    process_comparison_for_glicko(db, comparison.id)
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Error processing comparison {comparison.id} for Glicko-2: {e}")
                    error_count += 1
                    continue
            
            db.commit()
    except Exception as e:
        logger.error(f"Error in Glicko-2 calculation: {e}")
    finally:
        try:
            logger.info("Deleting glicko calculation in progress key")
            redis.delete("glicko_calculation_in_progress")
            logger.info("Glicko-2 calculation in progress key deleted")
        finally:
            redis.close()
            logger.info(f"All Glicko-2 calculations completed. Total processed: {processed_count}, Total errors: {error_count}")
    
    return {"processed": processed_count, "errors": error_count}


def get_or_create_model_glicko_leaderboard(db, model_id, metric_id, test_set_id, tag_id=None):
    """Get or create a model Glicko-2 leaderboard entry."""
    entry = db.execute(
        select(ModelGlickoLeaderboard).where(
            ModelGlickoLeaderboard.model_id == model_id,
            ModelGlickoLeaderboard.metric_id == metric_id,
            ModelGlickoLeaderboard.test_set_id == test_set_id,
            ModelGlickoLeaderboard.tag_id == tag_id,
        )
    ).scalar_one_or_none()

    if entry is None:
        entry = ModelGlickoLeaderboard(
            model_id=model_id,
            metric_id=metric_id,
            test_set_id=test_set_id,
            tag_id=tag_id,
            glicko_rating=1000.0,
            rating_deviation=350.0,
            volatility=0.06,
            vote_count=0,
            win_count=0,
            loss_count=0,
            tie_count=0,
        )
        db.add(entry)
        db.flush()

    return entry


def process_comparison_for_glicko(db, comparison_id):
    """
    Process a single comparison to update Glicko-2 scores.
    
    This function performs the following steps:
    1. Retrieves the comparison and ranks
    2. Extracts model and sample information
    3. Updates Glicko-2 ratings for models
    
    Args:
        db: Database session
        comparison_id: ID of the comparison to process
    """
    # Get comparison
    comparison = db.scalar(select(Comparison).where(Comparison.id == comparison_id))
    if not comparison:
        logger.error(f"Comparison {comparison_id} not found")
        return
    
    # Get comparison ranks
    ranks = db.scalars(
        select(ComparisonRank).where(ComparisonRank.comparison_id == comparison_id)
    ).all()
    
    if not ranks:
        logger.error(f"No ranks found for comparison {comparison_id}")
        return
    
    # Group sample IDs by rank
    samples_by_rank = defaultdict(list)
    for rank_entry in ranks:
        samples_by_rank[rank_entry.rank].append(rank_entry.sample_id)
    
    # Sort ranks (ascending: 1 is best, 2 is second, etc.)
    sorted_ranks = sorted(samples_by_rank.keys())
    
    if not sorted_ranks:
        logger.error(f"No valid ranks found for comparison {comparison_id}")
        return
    
    # Extract sample data
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
    
    # Check if it's a tie or win/loss situation
    is_tie = len(sorted_ranks) == 1
    
    # Setup leaderboard entries for models
    model_entries = {}  # (model_id, metric_id, test_set_id, tag_id) -> entry
    
    # Get model Glicko-2 leaderboard entries
    # First, get entries for global scores (no tag)
    for sample_id, data in sample_data.items():
        model_id = data["model_id"]
        model_key = (model_id, comparison.metric_id, comparison.test_set_id, None)
        if model_key not in model_entries:
            model_entries[model_key] = get_or_create_model_glicko_leaderboard(
                db, model_id, comparison.metric_id, comparison.test_set_id, None
            )
    
    # Then, get entries for tag-specific scores
    for sample_id, data in sample_data.items():
        model_id = data["model_id"]
        for tag_id in data.get("tag_ids", []):
            model_key = (model_id, comparison.metric_id, comparison.test_set_id, tag_id)
            if model_key not in model_entries:
                model_entries[model_key] = get_or_create_model_glicko_leaderboard(
                    db, model_id, comparison.metric_id, comparison.test_set_id, tag_id
                )
    
    # Process the comparison
    if is_tie:
        # Tie case - all samples have the same rank
        samples = [sample_id for rank in samples_by_rank.values() for sample_id in rank]
        
        # Process all sample pairs once
        for i in range(len(samples)):
            for j in range(i + 1, len(samples)):
                sample_a_id = samples[i]
                sample_b_id = samples[j]
                
                # Skip if either sample is missing data
                if sample_a_id not in sample_data or sample_b_id not in sample_data:
                    continue
                
                # Get sample data
                sample_a = sample_data[sample_a_id]
                sample_b = sample_data[sample_b_id]
                
                # MODEL GLICKO-2 UPDATE - TIE
                model_a_id = sample_a["model_id"]
                model_b_id = sample_b["model_id"]
                
                # Update global model entries (no tag)
                model_a_key = (model_a_id, comparison.metric_id, comparison.test_set_id, None)
                model_b_key = (model_b_id, comparison.metric_id, comparison.test_set_id, None)
                
                # Update vote count
                model_entries[model_a_key].vote_count += 1
                model_entries[model_b_key].vote_count += 1
                
                # Update tie count
                model_entries[model_a_key].tie_count += 1
                model_entries[model_b_key].tie_count += 1
                
                # Get current ratings
                model_a_rating = GlickoRating(
                    rating=model_entries[model_a_key].glicko_rating,
                    deviation=model_entries[model_a_key].rating_deviation,
                    volatility=model_entries[model_a_key].volatility
                )
                
                model_b_rating = GlickoRating(
                    rating=model_entries[model_b_key].glicko_rating,
                    deviation=model_entries[model_b_key].rating_deviation,
                    volatility=model_entries[model_b_key].volatility
                )
                
                # Create opponent rating lists
                model_a_opponents = [(model_b_rating, 0.5)]
                model_b_opponents = [(model_a_rating, 0.5)]  # 0.5 = tie
                
                # Calculate new ratings
                new_model_a_rating = update_glicko2_rating(model_a_rating, model_a_opponents)
                new_model_b_rating = update_glicko2_rating(model_b_rating, model_b_opponents)
                
                # Update model ratings
                model_entries[model_a_key].glicko_rating = new_model_a_rating.rating
                model_entries[model_a_key].rating_deviation = new_model_a_rating.deviation
                model_entries[model_a_key].volatility = new_model_a_rating.volatility
                
                model_entries[model_b_key].glicko_rating = new_model_b_rating.rating
                model_entries[model_b_key].rating_deviation = new_model_b_rating.deviation
                model_entries[model_b_key].volatility = new_model_b_rating.volatility
                
                # Also update tag-specific ratings if applicable
                for tag_id in set(sample_a.get("tag_ids", [])) & set(sample_b.get("tag_ids", [])):
                    model_a_tag_key = (model_a_id, comparison.metric_id, comparison.test_set_id, tag_id)
                    model_b_tag_key = (model_b_id, comparison.metric_id, comparison.test_set_id, tag_id)
                    
                    # Update vote count
                    model_entries[model_a_tag_key].vote_count += 1
                    model_entries[model_b_tag_key].vote_count += 1
                    
                    # Update tie count
                    model_entries[model_a_tag_key].tie_count += 1
                    model_entries[model_b_tag_key].tie_count += 1
                    
                    # Get current tag-specific ratings
                    model_a_tag_rating = GlickoRating(
                        rating=model_entries[model_a_tag_key].glicko_rating,
                        deviation=model_entries[model_a_tag_key].rating_deviation,
                        volatility=model_entries[model_a_tag_key].volatility
                    )
                    
                    model_b_tag_rating = GlickoRating(
                        rating=model_entries[model_b_tag_key].glicko_rating,
                        deviation=model_entries[model_b_tag_key].rating_deviation,
                        volatility=model_entries[model_b_tag_key].volatility
                    )
                    
                    # Create opponent rating lists
                    model_a_tag_opponents = [(model_b_tag_rating, 0.5)]  # 0.5 = tie
                    model_b_tag_opponents = [(model_a_tag_rating, 0.5)]  # 0.5 = tie
                    
                    # Calculate new ratings
                    new_model_a_tag_rating = update_glicko2_rating(model_a_tag_rating, model_a_tag_opponents)
                    new_model_b_tag_rating = update_glicko2_rating(model_b_tag_rating, model_b_tag_opponents)
                    
                    # Update model tag-specific ratings
                    model_entries[model_a_tag_key].glicko_rating = new_model_a_tag_rating.rating
                    model_entries[model_a_tag_key].rating_deviation = new_model_a_tag_rating.deviation
                    model_entries[model_a_tag_key].volatility = new_model_a_tag_rating.volatility
                    
                    model_entries[model_b_tag_key].glicko_rating = new_model_b_tag_rating.rating
                    model_entries[model_b_tag_key].rating_deviation = new_model_b_tag_rating.deviation
                    model_entries[model_b_tag_key].volatility = new_model_b_tag_rating.volatility
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
                
                # MODEL GLICKO-2 UPDATE - WIN/LOSS
                winner_model_id = winner["model_id"]
                loser_model_id = loser["model_id"]
                
                # Update global model entries (no tag)
                winner_model_key = (winner_model_id, comparison.metric_id, comparison.test_set_id, None)
                loser_model_key = (loser_model_id, comparison.metric_id, comparison.test_set_id, None)
                
                # Update vote count
                model_entries[winner_model_key].vote_count += 1
                model_entries[loser_model_key].vote_count += 1
                
                # Update win/loss count
                model_entries[winner_model_key].win_count += 1
                model_entries[loser_model_key].loss_count += 1
                
                # Get current ratings
                winner_model_rating = GlickoRating(
                    rating=model_entries[winner_model_key].glicko_rating,
                    deviation=model_entries[winner_model_key].rating_deviation,
                    volatility=model_entries[winner_model_key].volatility
                )
                
                loser_model_rating = GlickoRating(
                    rating=model_entries[loser_model_key].glicko_rating,
                    deviation=model_entries[loser_model_key].rating_deviation,
                    volatility=model_entries[loser_model_key].volatility
                )
                
                # Create opponent rating lists
                winner_model_opponents = [(loser_model_rating, 1.0)]  # 1.0 = win
                loser_model_opponents = [(winner_model_rating, 0.0)]  # 0.0 = loss
                
                # Calculate new ratings
                new_winner_model_rating = update_glicko2_rating(winner_model_rating, winner_model_opponents)
                new_loser_model_rating = update_glicko2_rating(loser_model_rating, loser_model_opponents)
                
                # Update model ratings
                model_entries[winner_model_key].glicko_rating = new_winner_model_rating.rating
                model_entries[winner_model_key].rating_deviation = new_winner_model_rating.deviation
                model_entries[winner_model_key].volatility = new_winner_model_rating.volatility
                
                model_entries[loser_model_key].glicko_rating = new_loser_model_rating.rating
                model_entries[loser_model_key].rating_deviation = new_loser_model_rating.deviation
                model_entries[loser_model_key].volatility = new_loser_model_rating.volatility
                
                # Also update tag-specific ratings if applicable
                for tag_id in set(winner.get("tag_ids", [])) & set(loser.get("tag_ids", [])):
                    winner_model_tag_key = (winner_model_id, comparison.metric_id, comparison.test_set_id, tag_id)
                    loser_model_tag_key = (loser_model_id, comparison.metric_id, comparison.test_set_id, tag_id)
                    
                    # Update vote count
                    model_entries[winner_model_tag_key].vote_count += 1
                    model_entries[loser_model_tag_key].vote_count += 1
                    
                    # Update win/loss count
                    model_entries[winner_model_tag_key].win_count += 1
                    model_entries[loser_model_tag_key].loss_count += 1
                    
                    # Get current tag-specific ratings
                    winner_model_tag_rating = GlickoRating(
                        rating=model_entries[winner_model_tag_key].glicko_rating,
                        deviation=model_entries[winner_model_tag_key].rating_deviation,
                        volatility=model_entries[winner_model_tag_key].volatility
                    )
                    
                    loser_model_tag_rating = GlickoRating(
                        rating=model_entries[loser_model_tag_key].glicko_rating,
                        deviation=model_entries[loser_model_tag_key].rating_deviation,
                        volatility=model_entries[loser_model_tag_key].volatility
                    )
                    
                    # Create opponent rating lists
                    winner_model_tag_opponents = [(loser_model_tag_rating, 1.0)]  # 1.0 = win
                    loser_model_tag_opponents = [(winner_model_tag_rating, 0.0)]  # 0.0 = loss
                    
                    # Calculate new ratings
                    new_winner_model_tag_rating = update_glicko2_rating(winner_model_tag_rating, winner_model_tag_opponents)
                    new_loser_model_tag_rating = update_glicko2_rating(loser_model_tag_rating, loser_model_tag_opponents)
                    
                    # Update model tag-specific ratings
                    model_entries[winner_model_tag_key].glicko_rating = new_winner_model_tag_rating.rating
                    model_entries[winner_model_tag_key].rating_deviation = new_winner_model_tag_rating.deviation
                    model_entries[winner_model_tag_key].volatility = new_winner_model_tag_rating.volatility
                    
                    model_entries[loser_model_tag_key].glicko_rating = new_loser_model_tag_rating.rating
                    model_entries[loser_model_tag_key].rating_deviation = new_loser_model_tag_rating.deviation
                    model_entries[loser_model_tag_key].volatility = new_loser_model_tag_rating.volatility
    
    # Mark the comparison as processed
    db.add(ProcessedComparison(comparison_id=comparison_id, created=datetime.datetime.now()))
    db.commit()
    
    logger.info(f"Successfully processed comparison {comparison_id} for Glicko-2 ratings")


@app.task(name="glicko_calculation.process_comparison")
def process_comparison_task(comparison_id):
    """Celery task wrapper for process_comparison_for_glicko."""
    with managed_session() as db:
        try:
            process_comparison_for_glicko(db, comparison_id)
            return f"Processed comparison {comparison_id} for Glicko-2 ratings"
        except Exception as e:
            logger.exception(f"Error processing comparison {comparison_id} for Glicko-2: {e}")
            return f"Error processing comparison {comparison_id} for Glicko-2: {e}" 