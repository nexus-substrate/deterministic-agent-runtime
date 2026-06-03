"""Decision trace models.

Every meaningful decision produces a trace — this is how we achieve
replayability and debuggability. See ADR-002.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.models.actions import Action


class DecisionReason(BaseModel):
    """Why a particular option was chosen or rejected."""

    stage: str  # e.g., "constraint", "fsm", "utility", "llm_advisory"
    description: str
    score: float | None = None


class DecisionTrace(BaseModel):
    """Full record of a decision — inputs, options, reasoning, outcome."""

    tick: int
    selected_action: Action
    alternatives_considered: list[Action] = Field(default_factory=list)
    reasons: list[DecisionReason] = Field(default_factory=list)
    constraints_checked: list[str] = Field(default_factory=list)
    constraints_violated: list[str] = Field(default_factory=list)
