import datetime
import uuid
from typing import Any, Dict, List, Optional

from .generic import Base


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


class SampleResponse(Base):
    id: uuid.UUID
    created: datetime.datetime
    result_inspiration_text: Optional[str] = None
    result_description_text: Optional[str] = None
    result_code_text: Optional[str] = None
    raw: Optional[str] = None
    last_modified: Optional[datetime.datetime] = None
    last_modified_by: Optional[str] = None


class ArtifactResponse(Base):
    id: uuid.UUID
    created: datetime.datetime
    kind: str
    bucket: str
    key: str


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
