import uuid
from typing import Dict, List, Optional

from .generic import Base


class NewComparisonBatchRequest(Base):
    batch_size: int = 3
    metric_id: uuid.UUID
    files: Optional[List[str]] = ("gltf_scene",)


class ComparisonDetailRequest(Base):
    token: uuid.UUID
    samples: List[uuid.UUID]


class UserComparisonRequest(Base):
    comparison_details: ComparisonDetailRequest
    # Best to worst
    ordered_sample_ids: List[uuid.UUID]


class SignupRequest(Base):
    username: str
    signup_auth_provider: str
    signup_auth_provider_data: Dict[str, str]


class LoginRequest(Base):
    login_auth_provider: str
    login_auth_provider_data: Dict[str, str]


class CreateUserRequest(Base):
    username: str
