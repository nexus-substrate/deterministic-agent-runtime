"""Typed Event Bus.

Central nervous system of the runtime. All inter-module communication
flows through typed events on this bus. Events are immutable records
with timestamps — never mutated after creation.

See ADR-001 for why events (not method calls) drive the system.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum


class EventType(StrEnum):
    """All valid event types in the runtime."""

    # Simulation events
    TICK = "tick"
    WORLD_CHANGED = "world_changed"

    # Agent events
    AGENT_MOVED = "agent_moved"
    AGENT_DAMAGED = "agent_damaged"
    AGENT_DIED = "agent_died"
    AGENT_ACTED = "agent_acted"

    # Decision events
    DECISION_MADE = "decision_made"
    CONSTRAINT_VIOLATED = "constraint_violated"
    CONSTRAINT_CHECKED = "constraint_checked"

    # Goal events
    GOAL_COMPLETED = "goal_completed"
    GOAL_FAILED = "goal_failed"

    # System events
    ANOMALY_DETECTED = "anomaly_detected"
    ESCALATION_REQUESTED = "escalation_requested"


@dataclass(frozen=True)
class Event:
    """An immutable event on the bus."""

    event_type: EventType
    tick: int
    data: dict[str, object] = field(default_factory=dict)


EventHandler = Callable[[Event], None]


class EventBus:
    """Typed, synchronous event bus with subscription and history.

    Events are dispatched synchronously in subscription order.
    The bus keeps a bounded history for replay and inspection.
    """

    def __init__(self, max_history: int = 10_000) -> None:
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._global_handlers: list[EventHandler] = []
        self._history: list[Event] = []
        self._max_history = max_history

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe to a specific event type."""
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe to all events (for logging, replay, telemetry)."""
        self._global_handlers.append(handler)

    def emit(self, event: Event) -> None:
        """Emit an event to all subscribers."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        for handler in self._global_handlers:
            handler(event)
        for handler in self._handlers.get(event.event_type, []):
            handler(event)

    def get_history(
        self,
        event_type: EventType | None = None,
        since_tick: int = 0,
    ) -> list[Event]:
        """Query event history with optional filtering."""
        events = self._history
        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]
        if since_tick > 0:
            events = [e for e in events if e.tick >= since_tick]
        return events

    def clear_history(self) -> None:
        """Clear event history (for testing)."""
        self._history.clear()

    @property
    def history_size(self) -> int:
        """Number of events in history."""
        return len(self._history)
