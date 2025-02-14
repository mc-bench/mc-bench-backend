import datetime
import uuid
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar

from .generic import Base

# Define the generic type variable
T = TypeVar("T")


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
    runs: List[RunResponse]


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
    active: bool
    usage: int
    tags: List[TagResponse]


class PromptResponse(PromptBaseResponse):
    pass


class PromptDetailResponse(PromptBaseResponse):
    runs: List[RunResponse]


class PromptCreatedResponse(Base):
    id: uuid.UUID


class ModelBaseResponse(Base):
    id: uuid.UUID
    created: datetime.datetime
    created_by: str
    last_modified: Optional[datetime.datetime]
    last_modified_by: Optional[str]
    slug: str
    providers: List[ProviderResponse]
    active: bool
    usage: int


class ModelResponse(ModelBaseResponse):
    pass


class ModelDetailResponse(ModelBaseResponse):
    runs: Optional[List[RunResponse]] = None


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


class TemplateResponse(TemplateBaseResponse):
    pass


class TemplateDetailResponse(TemplateBaseResponse):
    runs: List[RunResponse]


class RunRetryResponse(Base):
    pass


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
