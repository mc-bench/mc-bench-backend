import uuid
from typing import List

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
    url: str


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


class LeaderboardEntry(Base):
    model: str
    total_runs: int
    successful_runs: int
    success_rate: float


class LeaderboardResponse(Base):
    data: List[LeaderboardEntry]
