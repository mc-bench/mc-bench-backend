import uuid
from typing import List

from .generic import Base

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
