from typing import TypeVar

from pydantic import BaseModel


# Base event class that all events inherit from
class Event(BaseModel):
    pass


# Type variable for event types
E = TypeVar("E", bound=Event)
