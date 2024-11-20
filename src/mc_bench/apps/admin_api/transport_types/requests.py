import uuid
from typing import Any, Dict, List, Optional

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
    providers: List[CreateProviderRequest]


class CreatePromptRequest(Base):
    name: str
    build_specification: str
    active: bool


class UpdatePromptRequest(Base):
    name: Optional[str] = None
    active: Optional[bool] = None


class GenerationRequest(Base):
    name: str
    description: str
    prompt_ids: List[uuid.UUID]
    template_ids: List[uuid.UUID]
    model_ids: List[uuid.UUID]


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
