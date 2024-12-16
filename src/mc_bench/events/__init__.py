from typing import Any, Callable, Dict, List, Type

from .types import E, Event

_handlers: Dict[Type[Event], List[Callable]] = {}


def on_event(event_type: Type[E], fn: Callable[[E], Any]) -> None:
    """Register an event handler for a specific event type"""
    if event_type not in _handlers:
        _handlers[event_type] = []
    _handlers[event_type].append(fn)


def emit_event(event: Event) -> None:
    """Emit an event to all registered handlers"""
    event_type = type(event)
    if event_type in _handlers:
        for handler in _handlers[event_type]:
            handler(event)
