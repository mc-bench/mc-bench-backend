from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

class LeaderboardEntryResponse(BaseModel):
    elo_score: float
    vote_count: int
    win_count: int
    loss_count: int
    tie_count: int
    last_updated: str
    model: ModelResponse
    tag: Optional[TagResponse] = None


class LeaderboardResponse(BaseModel):
    metric: dict
    test_set_id: UUID
    test_set_name: str
    entries: List[LeaderboardEntryResponse]


class GlickoLeaderboardEntryResponse(BaseModel):
    glicko_rating: float
    rating_deviation: float
    volatility: float
    vote_count: int
    win_count: int
    loss_count: int
    tie_count: int
    last_updated: str
    model: ModelResponse
    tag: Optional[TagResponse] = None


class GlickoLeaderboardResponse(BaseModel):
    metric: dict
    test_set_id: UUID
    test_set_name: str
    entries: List[GlickoLeaderboardEntryResponse] 