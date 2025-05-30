import datetime
import uuid
from typing import List, Optional

from .generic import Base


class ValidateUsernameResponse(Base):
    is_valid: bool
    errors: List[str]


class LoginResponse(Base):
    user_id: uuid.UUID
    access_token: str
    refresh_token: str
    username: str


class SignupResponse(LoginResponse):
    pass


class SampleAssetDetailFile(Base):
    kind: str
    url: Optional[str] = None
    bucket: str
    key: str


class SampleAssetDetailResponse(Base):
    sample_id: uuid.UUID
    files: List[SampleAssetDetailFile]


class SamplesAssetDetailResponse(Base):
    assets: List[SampleAssetDetailResponse]


class Comparison(Base):
    token: uuid.UUID
    metric_id: uuid.UUID
    samples: List[uuid.UUID]
    build_description: str
    assets: List[SampleAssetDetailResponse]


class ComparisonBatchResponse(Base):
    comparisons: List[Comparison]


class MetricResponse(Base):
    id: uuid.UUID
    name: str
    description: str


class ModelResponse(Base):
    """Model information returned in leaderboard."""

    id: uuid.UUID
    name: str
    slug: str


class TagResponse(Base):
    """Tag information returned in leaderboard."""

    id: uuid.UUID
    name: str


class TestSetResponse(Base):
    """Test set information returned in API."""

    id: uuid.UUID
    name: str
    description: str


class LeaderboardEntryResponse(Base):
    """A single entry in the leaderboard."""

    elo_score: float
    vote_count: int
    win_count: int
    loss_count: int
    tie_count: int
    last_updated: str  # ISO format timestamp
    model: ModelResponse
    tag: Optional[TagResponse] = None


class LeaderboardResponse(Base):
    """Leaderboard data for a specific metric and test set."""

    metric: MetricResponse
    test_set_id: uuid.UUID
    test_set_name: str
    entries: List[LeaderboardEntryResponse]


class PromptLeaderboardEntryResponse(Base):
    """A single entry in the prompt leaderboard."""

    elo_score: float
    vote_count: int
    win_count: int
    loss_count: int
    tie_count: int
    last_updated: str  # ISO format timestamp
    prompt_id: uuid.UUID
    prompt_name: str
    tag: Optional[TagResponse] = None


class PagingResponse(Base):
    """Pagination information."""

    page: int
    page_size: int
    total_pages: int
    total_items: int
    has_next: bool
    has_previous: bool


class PromptLeaderboardResponse(Base):
    """Paged prompt leaderboard data for a specific model, metric and test set."""

    metric: MetricResponse
    test_set_id: uuid.UUID
    test_set_name: str
    model_id: uuid.UUID
    model_name: str
    model_slug: str
    entries: List[PromptLeaderboardEntryResponse]
    paging: PagingResponse


class ModelSamplesResponse(Base):
    """Paged samples for a specific model, metric and test set."""

    metric: MetricResponse
    test_set_id: uuid.UUID
    test_set_name: str
    model_id: uuid.UUID
    model_name: str
    model_slug: str
    samples: List["ModelSampleResponse"]
    paging: PagingResponse


class PromptResponse(Base):
    """Prompt information for sample view."""

    id: uuid.UUID
    name: str
    build_specification: str
    tags: List[TagResponse]


class RunInfoResponse(Base):
    """Basic run information for a sample."""

    model: ModelResponse
    prompt: PromptResponse
    template_name: str


class ArtifactResponse(Base):
    """Information about a sample artifact."""

    id: uuid.UUID
    kind: str
    bucket: str
    key: str


class SampleStatsResponse(Base):
    """Statistics about a sample's performance."""

    elo_score: Optional[float] = None
    vote_count: Optional[int] = None
    win_count: Optional[int] = None
    loss_count: Optional[int] = None
    tie_count: Optional[int] = None
    win_rate: Optional[float] = None
    last_updated: Optional[str] = None  # ISO format timestamp


class TopSampleResponse(Base):
    """Brief information about a top performing sample."""

    id: uuid.UUID
    elo_score: float
    win_rate: float
    vote_count: int
    prompt_id: uuid.UUID
    prompt_name: str


class BucketStatsResponse(Base):
    """Statistics for a bucket of samples."""

    bucket: int
    sample_count: int
    avg_elo: float
    win_rate: float
    total_votes: int
    total_wins: int
    total_losses: int
    total_ties: int
    model_name: str


class GlobalStatsResponse(Base):
    """Global statistics for a model's samples."""

    avg_elo: float
    total_votes: int
    total_wins: int
    total_losses: int
    total_ties: int
    win_rate: float


class ModelSampleStatsResponse(Base):
    """Complete statistics for a model's samples."""

    model: ModelResponse
    sample_count: int
    global_stats: Optional[GlobalStatsResponse] = None
    bucket_stats: Optional[List[BucketStatsResponse]] = None
    top_samples: Optional[List[TopSampleResponse]] = None
    statistics: Optional[dict] = None  # For error cases


class ModelSampleResponse(Base):
    """Sample statistics for leaderboard."""

    id: uuid.UUID
    elo_score: float
    win_rate: float
    vote_count: int
    win_count: int
    loss_count: int
    tie_count: int
    last_updated: Optional[str] = None  # ISO format timestamp
    prompt_name: Optional[str] = None


class SampleResponse(Base):
    """Public-facing sample information."""

    id: uuid.UUID
    created: datetime.datetime
    result_inspiration_text: Optional[str] = None
    result_description_text: Optional[str] = None
    result_code_text: Optional[str] = None
    is_complete: bool
    test_set_id: Optional[uuid.UUID] = None
    experimental_state: Optional[str] = None
    approval_state: Optional[str] = None
    run: RunInfoResponse
    artifacts: List[ArtifactResponse]
    stats: Optional[SampleStatsResponse] = None
