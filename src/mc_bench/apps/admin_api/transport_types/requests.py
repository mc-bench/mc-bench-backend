import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from .generic import Base


class CreateProviderRequest(Base):
    id: Optional[uuid.UUID] = None
    name: str
    provider_class: str
    config: Dict[str, Any]
    is_default: bool


class CreateModelRequest(Base):
    slug: str
    name: Optional[str] = None
    providers: List[CreateProviderRequest]


class CreatePromptRequest(Base):
    name: str
    build_specification: str
    build_size: Optional[str] = None
    active: bool
    tags: Optional[List[str]] = None


class UpdatePromptRequest(Base):
    name: Optional[str] = None
    active: Optional[bool] = None


class GenerationRequest(Base):
    name: str
    description: str
    prompt_ids: List[uuid.UUID]
    template_ids: List[uuid.UUID]
    model_ids: List[uuid.UUID]
    num_samples: int = 1


class CreateTemplateRequest(BaseModel):
    name: str
    description: str
    active: bool
    content: str


class UpdateTemplateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    content: Optional[str] = None


class UpdateModelRequest(Base):
    name: Optional[str] = None
    providers: Optional[List[CreateProviderRequest]] = None
    remove_providers: Optional[bool] = None
    content: Optional[str] = None
    active: Optional[bool] = None


class TaskRetryRequest(Base):
    tasks: List[str]


class StageProgress(Base):
    stage: str
    progress: float
    note: Optional[str] = None


class PagingRequest(Base):
    page: int = 1
    page_size: int = 50
    sort_by: Optional[str] = None
    sort_direction: Optional[str] = "asc"


class SampleApprovalState(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING_APPROVAL = "PENDING_APPROVAL"


class SampleFilterRequest(Base):
    model_id: Optional[Union[uuid.UUID, List[uuid.UUID]]] = None
    template_id: Optional[Union[uuid.UUID, List[uuid.UUID]]] = None
    prompt_id: Optional[Union[uuid.UUID, List[uuid.UUID]]] = None
    run_id: Optional[Union[uuid.UUID, List[uuid.UUID]]] = None
    approval_state: Optional[Union[SampleApprovalState, List[SampleApprovalState]]] = (
        None
    )
    pending: Optional[bool] = None
    complete: Optional[bool] = None


class SampleActionRequest(Base):
    note: str


class AddPromptTagRequest(Base):
    tag_name: str


class DeletePromptTagRequest(Base):
    tag_name: str


class PromptExperimentalStateProposalRequest(Base):
    current_state: str
    proposed_state: str
    note: Optional[str] = None


class ModelExperimentalStateProposalRequest(Base):
    current_state: str
    proposed_state: str
    note: Optional[str] = None


class TemplateExperimentalStateProposalRequest(Base):
    current_state: str
    proposed_state: str
    note: Optional[str] = None


class PromptExperimentalStateApprovalRequest(Base):
    note: Optional[str] = None


class PromptExperimentalStateRejectionRequest(Base):
    note: Optional[str] = None


class ModelExperimentalStateApprovalRequest(Base):
    note: Optional[str] = None


class ModelExperimentalStateRejectionRequest(Base):
    note: Optional[str] = None


class TemplateExperimentalStateApprovalRequest(Base):
    note: Optional[str] = None


class TemplateExperimentalStateRejectionRequest(Base):
    note: Optional[str] = None


class PromptObservationRequest(Base):
    note: str


class ModelObservationRequest(Base):
    note: str


class TemplateObservationRequest(Base):
    note: str


class UpdateRolesRequest(Base):
    roles: List[uuid.UUID]


class CancelConsumerRequest(Base):
    """Request to cancel a worker's consumption from a queue."""

    queue: str


class WorkerActionRequest(Base):
    """Request to perform an action on a worker."""

    action: str  # Can be "shutdown", "restart", "pool_grow", "pool_shrink"
    option: Optional[Any] = None  # Additional option for the action if needed
