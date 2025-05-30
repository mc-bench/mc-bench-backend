"""
Utility functions for ELO rating calculations.

This module provides pure mathematical functions for calculating and updating ELO ratings.
These functions are separated from database operations for easier testing and reuse.
"""

import math
from enum import Enum
from typing import Dict, Tuple


class Outcome(Enum):
    """Possible outcomes of a comparison."""

    WIN = 1.0
    LOSS = 0.0
    TIE = 0.5


def expected_score(rating_a: float, rating_b: float) -> float:
    """
    Calculate expected score (winning probability) for player A when facing player B.

    Args:
        rating_a: ELO rating of player A
        rating_b: ELO rating of player B

    Returns:
        Expected probability of player A winning against player B
    """
    return 1.0 / (1.0 + math.pow(10, (rating_b - rating_a) / 400.0))


def calculate_new_rating(
    rating: float, expected: float, actual: float, k_factor: float
) -> float:
    """
    Calculate new ELO rating based on expected and actual outcome.

    Args:
        rating: Current ELO rating
        expected: Expected score (probability of winning)
        actual: Actual outcome (1.0 for win, 0.0 for loss, 0.5 for tie)
        k_factor: K-factor determining the maximum possible adjustment

    Returns:
        New ELO rating
    """
    return rating + k_factor * (actual - expected)


def update_elo(
    rating: float, expected: float, actual: float, k_factor: float, min_score: float
) -> float:
    """
    Update ELO rating based on expected and actual outcome, enforcing a minimum score.

    Args:
        rating: Current ELO rating
        expected: Expected score (probability of winning)
        actual: Actual outcome (1.0 for win, 0.0 for loss, 0.5 for tie)
        k_factor: K-factor determining the maximum possible adjustment
        min_score: Minimum allowable score

    Returns:
        New ELO rating, guaranteed to be at least min_score
    """
    new_rating = calculate_new_rating(rating, expected, actual, k_factor)
    return max(min_score, new_rating)


def determine_outcome(rank_a: int, rank_b: int) -> Tuple[float, float]:
    """
    Determine the outcome of a comparison based on the ranks.
    Lower rank is better.

    Args:
        rank_a: Rank of the first player/item
        rank_b: Rank of the second player/item

    Returns:
        Tuple of (player_a_outcome, player_b_outcome)
    """
    if rank_a < rank_b:  # A wins
        return Outcome.WIN.value, Outcome.LOSS.value
    elif rank_a > rank_b:  # B wins
        return Outcome.LOSS.value, Outcome.WIN.value
    else:  # tie
        return Outcome.TIE.value, Outcome.TIE.value


def calculate_pairwise_elo_updates(
    id_a: str,
    id_b: str,
    rating_a: float,
    rating_b: float,
    rank_a: int,
    rank_b: int,
    k_factor: float,
    min_score: float,
) -> Dict[str, float]:
    """
    Calculate ELO updates for a pairwise comparison.

    Args:
        id_a: Identifier for the first player/item
        id_b: Identifier for the second player/item
        rating_a: Current ELO rating of the first player/item
        rating_b: Current ELO rating of the second player/item
        rank_a: Rank of the first player/item (lower is better)
        rank_b: Rank of the second player/item (lower is better)
        k_factor: K-factor determining the maximum possible adjustment
        min_score: Minimum allowable score

    Returns:
        Dictionary mapping player/item IDs to their new ELO ratings
    """
    # Calculate expected scores
    expected_a = expected_score(rating_a, rating_b)
    expected_b = expected_score(rating_b, rating_a)

    # Determine actual outcomes
    actual_a, actual_b = determine_outcome(rank_a, rank_b)

    # Calculate new ratings
    new_rating_a = update_elo(rating_a, expected_a, actual_a, k_factor, min_score)
    new_rating_b = update_elo(rating_b, expected_b, actual_b, k_factor, min_score)

    return {id_a: new_rating_a, id_b: new_rating_b}


def calculate_multiway_elo_updates(
    ratings: Dict[str, float], ranks: Dict[str, int], k_factor: float, min_score: float
) -> Dict[str, float]:
    """
    Calculate ELO updates for a multi-way comparison.

    Handles multiple comparisons with potentially tied ranks.
    Each entity (identified by its ID) is compared against all others.
    The resulting ELO ratings are averaged from all pairwise comparisons.

    Args:
        ratings: Dictionary mapping entity IDs to their current ELO ratings
        ranks: Dictionary mapping entity IDs to their ranks (lower is better)
        k_factor: K-factor determining the maximum possible adjustment
        min_score: Minimum allowable score

    Returns:
        Dictionary mapping entity IDs to their new ELO ratings
    """
    # Track updates for each entity
    updates = {entity_id: {"sum": 0.0, "count": 0} for entity_id in ratings}

    # For each pair of entities
    ids = list(ratings.keys())
    for i, id_a in enumerate(ids):
        for id_b in ids[i + 1 :]:
            # Get ratings and ranks
            rating_a = ratings[id_a]
            rating_b = ratings[id_b]
            rank_a = ranks[id_a]
            rank_b = ranks[id_b]

            # Calculate pairwise updates
            pairwise_updates = calculate_pairwise_elo_updates(
                id_a, id_b, rating_a, rating_b, rank_a, rank_b, k_factor, min_score
            )

            # Accumulate updates
            for entity_id, new_rating in pairwise_updates.items():
                updates[entity_id]["sum"] += new_rating
                updates[entity_id]["count"] += 1

    # Average the updates
    result = {}
    for entity_id, update_data in updates.items():
        if update_data["count"] > 0:
            result[entity_id] = update_data["sum"] / update_data["count"]
        else:
            result[entity_id] = ratings[
                entity_id
            ]  # Keep original rating if no comparisons

    return result
