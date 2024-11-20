from typing import Generic, List, TypeVar

import humps
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class Base(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,  # Enables ORM model parsing
        alias_generator=humps.camelize,  # Converts snake_case to camelCase
        populate_by_name=True,  # Allows accessing fields by snake_case name
        arbitrary_types_allowed=True,
    )


class ListResponse(Base, Generic[T]):
    data: List[T]
    total: int
