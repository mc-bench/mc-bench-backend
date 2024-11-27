import uuid
from typing import List

from .generic import Base


class Comparison(Base):
    token: uuid.UUID
    metric_id: uuid.UUID
    samples: List[uuid.UUID]
    build_description: str


class ComparisonBatchResponse(Base):
    comparisons: List[Comparison]


class MetricResponse(Base):
    id: uuid.UUID
    name: str
    description: str
