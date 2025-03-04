import datetime
import uuid
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar

from .generic import Base

# Define the generic type variable
T = TypeVar("T")


class BaseProposalResponse(Base):
    id: uuid.UUID
    created: datetime.datetime
    created_by: str
    proposed_state: str
    accepted: Optional[bool] = None
    accepted_at: Optional[datetime.datetime] = None
    accepted_by: Optional[str] = None
    rejected: Optional[bool] = None
    rejected_at: Optional[datetime.datetime] = None
    rejected_by: Optional[str] = None


class ProposalResponse(BaseProposalResponse):
    pass


class TagResponse(Base):
    id: uuid.UUID
    name: str


class LogResponse(Base):
    id: uuid.UUID
    created: datetime.datetime
    created_by: str
    note: str
    kind: str
    action: str
    proposal: Optional[ProposalResponse] = None


class ProposalResponseDetail(BaseProposalResponse):
    log: Optional[LogResponse] = None
    accepted_log: Optional[LogResponse] = None
    rejected_log: Optional[LogResponse] = None


class RunBaseResponse(Base):
    id: uuid.UUID
    created: datetime.datetime
    created_by: str
    last_modified: Optional[datetime.datetime] = None
    last_modified_by: Optional[str] = None
    prompt: "PromptResponse"
    model: "ModelResponse"
    template: "TemplateResponse"
    status: str
    generation_id: Optional[uuid.UUID] = None
    latest_completed_stage: Optional[str] = None
    earliest_in_progress_stage: Optional[str] = None


class RunResponse(RunBaseResponse):
    pass


class RunStageResponse(Base):
    id: uuid.UUID
    stage: str
    state: str
    progress: float
    note: Optional[str] = None


class RunStatusResponse(Base):
    id: uuid.UUID
    status: str
    stages: List["RunStageResponse"]


class RunDetailResponse(RunBaseResponse):
    samples: List["SampleResponse"]
    artifacts: List["ArtifactResponse"]
    stages: List["RunStageResponse"]


class ModelInfo(Base):
    slug: str


class PromptInfo(Base):
    name: str


class TemplateInfo(Base):
    name: str


class RunInfo(Base):
    model: "ModelInfo"
    prompt: "PromptInfo"
    template: "TemplateInfo"


class ArtifactResponse(Base):
    id: uuid.UUID
    created: datetime.datetime
    kind: str
    bucket: str
    key: str


class SampleResponse(Base):
    id: uuid.UUID
    created: datetime.datetime
    created_by: str
    result_inspiration_text: Optional[str] = None
    result_description_text: Optional[str] = None
    result_code_text: Optional[str] = None
    raw: Optional[str] = None
    last_modified: Optional[datetime.datetime] = None
    last_modified_by: Optional[str] = None
    is_pending: bool
    is_complete: bool
    approval_state: Optional[Literal["APPROVED", "REJECTED", None]] = None
    run: Optional[RunInfo] = None
    experimental_state: Optional[str] = None


class SampleDetailResponse(SampleResponse):
    logs: List[LogResponse]
    artifacts: List[ArtifactResponse]
    run: RunBaseResponse


class GenerationBaseResponse(Base):
    id: uuid.UUID
    created: datetime.datetime
    created_by: str
    name: str
    description: str
    run_count: int
    status: str


class GenerationResponse(GenerationBaseResponse):
    pending_runs: int
    completed_runs: int
    failed_runs: int


class GenerationDetailResponse(GenerationResponse):
    runs: Optional[List[RunResponse]] = None


class GenerationCreatedResponse(Base):
    id: uuid.UUID


class ProviderResponse(Base):
    id: uuid.UUID
    name: str
    provider_class: str
    config: Dict[str, Any]
    is_default: bool


class ProviderClassResponse(Base):
    id: uuid.UUID
    name: str


class RunGenerationResponse(Base):
    id: uuid.UUID


class PromptBaseResponse(Base):
    id: uuid.UUID
    created: datetime.datetime
    created_by: str
    name: str
    last_modified: Optional[datetime.datetime] = None
    last_modified_by: Optional[str] = None
    build_specification: str
    build_size: Optional[str] = None
    active: bool
    usage: int
    observational_note_count: int
    pending_proposal_count: int
    tags: List[TagResponse]
    experimental_state: Optional[str] = None


class PromptResponse(PromptBaseResponse):
    pass


class PromptDetailResponse(PromptBaseResponse):
    runs: Optional[List[RunResponse]] = None
    logs: List[LogResponse]
    proposals: List[ProposalResponseDetail]


class PromptCreatedResponse(Base):
    id: uuid.UUID


class ModelBaseResponse(Base):
    id: uuid.UUID
    created: datetime.datetime
    created_by: str
    last_modified: Optional[datetime.datetime]
    last_modified_by: Optional[str]
    slug: str
    name: str
    providers: List[ProviderResponse]
    active: bool
    usage: int
    observational_note_count: int
    pending_proposal_count: int
    experimental_state: Optional[str] = None


class ModelResponse(ModelBaseResponse):
    pass


class ModelDetailResponse(ModelBaseResponse):
    runs: Optional[List[RunResponse]] = None
    logs: List[LogResponse]
    proposals: List[ProposalResponseDetail]


class ModelCreatedResponse(Base):
    id: uuid.UUID


class TemplateCreatedResponse(Base):
    id: uuid.UUID


class TemplateBaseResponse(Base):
    id: uuid.UUID
    created: datetime.datetime
    created_by: str
    last_modified: Optional[datetime.datetime] = None
    last_modified_by: Optional[str] = None
    name: str
    description: str
    content: str
    active: bool
    frozen: bool
    usage: int
    observational_note_count: int
    pending_proposal_count: int
    experimental_state: Optional[str] = None


class TemplateResponse(TemplateBaseResponse):
    pass


class TemplateDetailResponse(TemplateBaseResponse):
    runs: Optional[List[RunResponse]] = None
    logs: List[LogResponse]
    proposals: List[ProposalResponseDetail]


class ExperimentalStateResponse(Base):
    id: uuid.UUID
    name: str


class RunRetryResponse(Base):
    pass


class RunStagesResponse(Base):
    """Response for available run stages."""

    data: List[str]


class PagingResponse(Base):
    page: int
    page_size: int
    total_pages: int
    total_items: int
    has_next: bool
    has_previous: bool


class PagedListResponse(Base, Generic[T]):
    data: List[T]
    paging: PagingResponse


class TagListChangeResponse(Base):
    current_tags: List[TagResponse]


class RoleResponse(Base):
    id: uuid.UUID
    name: str
    permissions: List[str]


class UserResponse(Base):
    id: uuid.UUID
    username: str
    roles: List[RoleResponse]
    permissions: List[str]


class WorkerTaskResponse(Base):
    """Information about a task being processed by a worker."""

    id: str
    name: str
    started_at: Optional[datetime.datetime] = None
    args: List[Any]
    kwargs: Dict[str, Any]
    status: str
    eta: Optional[datetime.datetime] = None
    retries: int = 0


class WorkerResponse(Base):
    """Information about a Celery worker."""

    id: str
    hostname: str
    status: str
    display_name: str = ""  # Formatted name for UI display (container@node)
    container_name: str = ""  # Container part of the worker name
    node_name: str = ""  # Node part of the worker name
    queues: List[str]
    concurrency: int
    pool_size: int
    tasks: List[WorkerTaskResponse]
    last_heartbeat: Optional[datetime.datetime] = None
    started_at: Optional[datetime.datetime] = None


class QueuedTaskResponse(Base):
    """Information about a task in the queue not yet picked up."""

    id: str
    name: str
    args: List[Any]
    kwargs: Dict[str, Any]
    eta: Optional[datetime.datetime] = None
    priority: Optional[int] = None
    queued_at: Optional[datetime.datetime] = None


class QueueResponse(Base):
    """Information about a Celery queue."""

    name: str
    count: int
    tasks: List[QueuedTaskResponse]
    worker_count: int


class InfraStatusResponse(Base):
    """Overall infrastructure status."""

    workers: List[WorkerResponse]
    queues: List[QueueResponse]
    total_active_tasks: int
    total_queued_tasks: int
    warnings: List[str]


class CancelConsumerResponse(Base):
    """Response for cancelling a consumer."""

    success: bool
    message: str
