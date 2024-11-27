import uuid
from typing import List

from .generic import Base


class NewComparisonBatchRequest(Base):
    batch_size: int = 3
    metric_id: uuid.UUID


class ComparisonDetailRequest(Base):
    token: uuid.UUID
    samples: List[uuid.UUID]


class UserComparisonRequest(Base):
    comparison_details: ComparisonDetailRequest
    # Best to worst
    ordered_sample_ids: List[uuid.UUID]
