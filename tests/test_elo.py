"""
Tests for the ELO calculation utilities.
"""

import pytest

from mc_bench.util.elo import (
    Outcome,
    calculate_multiway_elo_updates,
    calculate_new_rating,
    calculate_pairwise_elo_updates,
    determine_outcome,
    expected_score,
    update_elo,
)


@pytest.mark.parametrize(
    "rating_a, rating_b, expected_result",
    [
        (1000, 1000, 0.5),  # Equal ratings
        (1200, 1000, 0.7597),  # Higher rating advantage
        (1000, 1200, 0.2403),  # Lower rating disadvantage
        (2000, 1000, 0.9968),  # Large advantage
        (1000, 2000, 0.0032),  # Large disadvantage
        (1500, 1400, 0.6401),  # Small advantage
        (1400, 1500, 0.3599),  # Small disadvantage
    ],
)
def test_expected_score(rating_a, rating_b, expected_result):
    """Test expected score calculations with various rating differences."""
    result = expected_score(rating_a, rating_b)
    assert round(result, 4) == expected_result


@pytest.mark.parametrize(
    "rating, expected, actual, k_factor, expected_change",
    [
        (1000, 0.5, 1.0, 32, 16),  # Win when expected 0.5
        (1000, 0.5, 0.0, 32, -16),  # Loss when expected 0.5
        (1000, 0.5, 0.5, 32, 0),  # Tie when expected 0.5
        (1000, 0.75, 1.0, 32, 8),  # Win when expected 0.75
        (1000, 0.25, 0.0, 32, -8),  # Loss when expected 0.25
        (1000, 0.5, 1.0, 16, 8),  # Win with lower K-factor
        (1000, 0.5, 0.0, 48, -24),  # Loss with higher K-factor
        (1000, 0.9, 0.0, 32, -28.8),  # Upset loss (expected to win)
        (1000, 0.1, 1.0, 32, 28.8),  # Upset win (expected to lose)
    ],
)
def test_calculate_new_rating(rating, expected, actual, k_factor, expected_change):
    """Test calculation of new ratings with various inputs."""
    new_rating = calculate_new_rating(rating, expected, actual, k_factor)
    assert new_rating == rating + expected_change

    # Verify expected behavior based on outcome
    if actual > expected:
        assert new_rating > rating
    elif actual < expected:
        assert new_rating < rating
    else:
        assert new_rating == rating


@pytest.mark.parametrize(
    "rating, expected, actual, k_factor, min_score, expected_result",
    [
        (1000, 0.5, 0.0, 32, 100, 984),  # Normal decrease above minimum
        (110, 0.5, 0.0, 32, 100, 100),  # Decrease would go below minimum
        (100, 0.5, 0.0, 32, 100, 100),  # Already at minimum, can't go lower
        (120, 0.75, 0.0, 40, 100, 100),  # Large decrease would go below minimum
        (1000, 0.5, 1.0, 32, 100, 1016),  # Increase not affected by minimum
    ],
)
def test_update_elo(rating, expected, actual, k_factor, min_score, expected_result):
    """Test Elo updates with minimum score enforcement."""
    new_rating = update_elo(rating, expected, actual, k_factor, min_score)
    assert new_rating == expected_result

    # Verify minimum score is respected
    assert new_rating >= min_score

    # Verify raw calculation vs minimum enforcement
    raw_calculation = rating + k_factor * (actual - expected)
    if raw_calculation < min_score:
        assert new_rating == min_score
    else:
        assert new_rating == raw_calculation


@pytest.mark.parametrize(
    "rank_a, rank_b, expected_outcome_a, expected_outcome_b",
    [
        (1, 2, Outcome.WIN.value, Outcome.LOSS.value),  # A wins (lower rank)
        (2, 1, Outcome.LOSS.value, Outcome.WIN.value),  # B wins (lower rank)
        (3, 3, Outcome.TIE.value, Outcome.TIE.value),  # Tie (equal ranks)
        (0, 1, Outcome.WIN.value, Outcome.LOSS.value),  # Zero rank wins
        (10, 20, Outcome.WIN.value, Outcome.LOSS.value),  # Large rank difference
    ],
)
def test_determine_outcome(rank_a, rank_b, expected_outcome_a, expected_outcome_b):
    """Test outcome determination based on ranks."""
    outcome_a, outcome_b = determine_outcome(rank_a, rank_b)
    assert outcome_a == expected_outcome_a
    assert outcome_b == expected_outcome_b

    # Outcomes should be opposites, except for ties
    if rank_a == rank_b:
        assert outcome_a == outcome_b == Outcome.TIE.value
    else:
        assert outcome_a != outcome_b
        assert outcome_a + outcome_b == 1.0  # Win (1.0) + Loss (0.0) = 1.0


@pytest.mark.parametrize(
    "id_a, id_b, rating_a, rating_b, rank_a, rank_b, k_factor, min_score, expected_changes",
    [
        # Equal ratings, a wins
        ("a", "b", 1000, 1000, 1, 2, 32, 100, {"a": 16, "b": -16}),
        # Equal ratings, tie
        ("a", "b", 1000, 1000, 1, 1, 32, 100, {"a": 0, "b": 0}),
        # Underdog wins (a < b in rating, but a wins)
        ("a", "b", 1000, 1200, 1, 2, 32, 100, {"a": 24.31, "b": -24.31}),
        # Favorite wins (a > b in rating, and a wins)
        ("a", "b", 1200, 1000, 1, 2, 32, 100, {"a": 7.69, "b": -7.69}),
        # Near minimum score
        ("a", "b", 110, 1000, 2, 1, 32, 100, {"a": -0.19, "b": 0.19}),
    ],
)
def test_calculate_pairwise_elo_updates(
    id_a,
    id_b,
    rating_a,
    rating_b,
    rank_a,
    rank_b,
    k_factor,
    min_score,
    expected_changes,
):
    """Test pairwise ELO updates with various initial conditions."""
    updates = calculate_pairwise_elo_updates(
        id_a, id_b, rating_a, rating_b, rank_a, rank_b, k_factor, min_score
    )

    # Check that updates have the right IDs
    assert set(updates.keys()) == {id_a, id_b}

    # Check that the magnitude of changes matches expectations (within a small tolerance)
    tolerance = 0.01  # Allow for small floating-point differences
    assert abs((updates[id_a] - rating_a) - expected_changes[id_a]) < tolerance
    assert abs((updates[id_b] - rating_b) - expected_changes[id_b]) < tolerance

    # Additional checks based on outcome
    if rank_a < rank_b:  # a wins
        assert updates[id_a] > rating_a
        assert updates[id_b] < rating_b
    elif rank_a > rank_b:  # b wins
        assert updates[id_a] < rating_a
        assert updates[id_b] > rating_b
    else:  # tie
        if rating_a == rating_b:
            assert updates[id_a] == rating_a
            assert updates[id_b] == rating_b
        elif rating_a > rating_b:  # a expected to win but tied
            assert updates[id_a] < rating_a
            assert updates[id_b] > rating_b
        else:  # b expected to win but tied
            assert updates[id_a] > rating_a
            assert updates[id_b] < rating_b


@pytest.mark.parametrize(
    "ratings, ranks, k_factor, min_score, expected_directions, significant_changes",
    [
        # All equal ratings, clear ranking
        (
            {"a": 1000, "b": 1000, "c": 1000},
            {"a": 1, "b": 2, "c": 3},
            32,
            100,
            {"a": 1, "b": 0, "c": -1},  # 1=increase, 0=may change, -1=decrease
            ["a", "c"],  # entities expected to change significantly
        ),
        # All equal ratings, with ties
        (
            {"a": 1000, "b": 1000, "c": 1000, "d": 1000},
            {"a": 1, "b": 1, "c": 2, "d": 2},
            32,
            100,
            {"a": 1, "b": 1, "c": -1, "d": -1},
            [],  # not all changes are significant with our implementation
        ),
        # Different ratings, ranks match expectations
        (
            {"a": 1200, "b": 1000, "c": 800},
            {"a": 1, "b": 2, "c": 3},
            32,
            100,
            {"a": 0, "b": 0, "c": 0},
            [],
        ),
        # Upset victory
        (
            {"a": 1200, "b": 1000, "c": 800},
            {"a": 3, "b": 2, "c": 1},
            32,
            100,
            {"a": -1, "b": 0, "c": 1},
            ["a", "c"],
        ),
        # All tied
        (
            {"a": 1000, "b": 1000, "c": 1000},
            {"a": 1, "b": 1, "c": 1},
            32,
            100,
            {"a": 0, "b": 0, "c": 0},
            [],
        ),
    ],
)
def test_calculate_multiway_elo_updates(
    ratings, ranks, k_factor, min_score, expected_directions, significant_changes
):
    """Test multi-way ELO updates with various scenarios."""
    updates = calculate_multiway_elo_updates(ratings, ranks, k_factor, min_score)

    # Check that all entities are in the results
    assert set(updates.keys()) == set(ratings.keys())

    # Check expected direction of changes
    for entity_id, direction in expected_directions.items():
        if direction == 1:
            assert updates[entity_id] > ratings[entity_id]
        elif direction == -1:
            assert updates[entity_id] < ratings[entity_id]

    # Check entities that should have significant changes
    significant_threshold = 15
    for entity_id in significant_changes:
        assert abs(updates[entity_id] - ratings[entity_id]) > significant_threshold

    # For all entities not in significant_changes, changes should be smaller
    for entity_id in set(ratings.keys()) - set(significant_changes):
        if entity_id in expected_directions and expected_directions[entity_id] != 0:
            # The entity should change but not significantly
            assert (
                0
                < abs(updates[entity_id] - ratings[entity_id])
                <= significant_threshold
            )

    # For special case: if all ranks are tied, no ratings should change
    if len(set(ranks.values())) == 1:
        for entity_id in ratings:
            assert updates[entity_id] == ratings[entity_id]
