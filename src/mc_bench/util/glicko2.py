"""
Utility functions for Glicko-2 ratings.

This module provides functions to calculate and update Glicko-2 ratings.
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


# Constants used in the Glicko-2 calculations
TAU = 0.5  # System constant that constrains rating volatility changes
EPSILON = 0.000001  # Convergence threshold


class Outcome(Enum):
    """Possible outcomes of a match."""
    WIN = 1.0
    LOSS = 0.0
    DRAW = 0.5


@dataclass
class GlickoRating:
    """
    Represents a Glicko-2 rating.
    
    Attributes:
        rating: The player's rating
        deviation: The rating deviation (RD)
        volatility: The rating volatility
    """
    rating: float
    deviation: float
    volatility: float


def g(deviation: float) -> float:
    """
    Calculates the g function used in the Glicko-2 algorithm.
    
    Args:
        deviation: Rating deviation
        
    Returns:
        The calculated g value
    """
    return 1.0 / math.sqrt(1.0 + (3.0 * deviation**2) / (math.pi**2))


def E(rating: float, opponent_rating: float, opponent_deviation: float) -> float:
    """
    Calculates the expected outcome (E function) of a match.
    
    Args:
        rating: Player's rating
        opponent_rating: Opponent's rating
        opponent_deviation: Opponent's rating deviation
        
    Returns:
        The expected outcome value (between 0 and 1)
    """
    return 1.0 / (1.0 + math.exp(-g(opponent_deviation) * (rating - opponent_rating) / 400.0))


def f(x: float, delta: float, deviation: float, volatility: float, v: float) -> float:
    """
    Calculates the f function used in the volatility update algorithm.
    
    Args:
        x: Current estimate
        delta: The estimated improvement in rating
        deviation: The rating deviation
        volatility: The rating volatility
        v: The variance of the rating estimate
        
    Returns:
        The calculated f value
    """
    ex = math.exp(x)
    part1 = ex * (delta**2 - deviation**2 - v - ex) / (2.0 * (deviation**2 + v + ex)**2)
    part2 = (x - math.log(volatility**2)) / TAU**2
    return part1 - part2


def update_glicko2_rating(
    rating: GlickoRating, 
    opponents: List[Tuple[GlickoRating, float]]
) -> GlickoRating:
    """
    Updates a player's Glicko-2 rating based on match outcomes.
    
    Args:
        rating: The player's current rating
        opponents: List of (opponent_rating, outcome) pairs, where outcome is 1 for win, 0.5 for draw, 0 for loss
        
    Returns:
        The updated Glicko-2 rating
    """
    # Step 1: Convert from Glicko to Glicko-2 scale
    mu = (rating.rating - 1500) / 173.7178
    phi = rating.deviation / 173.7178
    sigma = rating.volatility
    
    # If no games were played, increase deviation and return
    if not opponents:
        new_phi = math.sqrt(phi**2 + sigma**2)
        return GlickoRating(
            rating=rating.rating,
            deviation=min(350, 173.7178 * new_phi),  # Cap RD at 350
            volatility=sigma
        )
    
    # Step 2: Calculate v (estimated variance of the team's rating)
    v = 0.0
    for opponent_rating, _ in opponents:
        # Convert opponent to Glicko-2 scale
        opp_mu = (opponent_rating.rating - 1500) / 173.7178
        opp_phi = opponent_rating.deviation / 173.7178
        
        v_i = g(opp_phi)**2 * E(mu, opp_mu, opp_phi) * (1 - E(mu, opp_mu, opp_phi))
        v += v_i
    
    v = 1.0 / v if v != 0 else 0.0
    
    # Step 3: Calculate delta (estimated improvement)
    delta = 0.0
    for opponent_rating, outcome in opponents:
        # Convert opponent to Glicko-2 scale
        opp_mu = (opponent_rating.rating - 1500) / 173.7178
        opp_phi = opponent_rating.deviation / 173.7178
        
        delta += g(opp_phi) * (outcome - E(mu, opp_mu, opp_phi))
    
    delta = v * delta
    
    # Step 4: Calculate new volatility (sigma')
    a = math.log(sigma**2)
    
    # Initial values for iterative algorithm
    A = a
    B = 0.0
    
    if delta**2 > phi**2 + v:
        B = math.log(delta**2 - phi**2 - v)
    else:
        k = 1
        while f(a - k * TAU, delta, phi, sigma, v) < 0:
            k += 1
        B = a - k * TAU
    
    # Iterative algorithm to find new volatility
    fa = f(A, delta, phi, sigma, v)
    fb = f(B, delta, phi, sigma, v)
    
    while abs(B - A) > EPSILON:
        C = A + (A - B) * fa / (fb - fa)
        fc = f(C, delta, phi, sigma, v)
        
        if fc * fb <= 0:
            A = B
            fa = fb
        else:
            fa = fa / 2
        
        B = C
        fb = fc
    
    sigma_prime = math.exp(A / 2)
    
    # Step 5: Calculate new phi (rating deviation)
    phi_star = math.sqrt(phi**2 + sigma_prime**2)
    phi_prime = 1.0 / math.sqrt((1.0 / phi_star**2) + (1.0 / v)) if v != 0 else phi_star
    
    # Step 6: Calculate new mu (rating)
    mu_prime = mu + phi_prime**2 * sum(g(opp_phi) * (outcome - E(mu, opp_mu, opp_phi)) 
                                       for opp_rating, outcome in opponents 
                                       for opp_mu, opp_phi in [((opp_rating.rating - 1500) / 173.7178, 
                                                                 opp_rating.deviation / 173.7178)])
    
    # Step 7: Convert back to Glicko scale
    new_rating = 173.7178 * mu_prime + 1500
    new_deviation = 173.7178 * phi_prime
    
    # Ensure deviation stays within bounds
    new_deviation = min(350, max(30, new_deviation))
    
    return GlickoRating(
        rating=new_rating,
        deviation=new_deviation,
        volatility=sigma_prime
    ) 