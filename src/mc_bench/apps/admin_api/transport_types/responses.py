import datetime
import uuid
from typing import Any, Dict, List, Optional

from .generic import Base


class RunsResponse(Base):
    id: uuid.UUID
    created: datetime.datetime
    created_by: str
    last_modified: Optional[datetime.datetime] = None
    last_modified_by: Optional[str] = None
    prompt: "PromptResponse"
    model: "ModelResponse"
    template: "TemplateResponse"
    status: str


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
    runs: List[RunsResponse]


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
    runs: List[RunsResponse]


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
    runs: Optional[List[RunsResponse]] = None


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
    runs: List[RunsResponse]
