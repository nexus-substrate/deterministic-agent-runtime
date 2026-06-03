"""Goal models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class GoalStatus(StrEnum):
    """Goal lifecycle status."""

    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class Goal(BaseModel):
    """What the agent is trying to achieve."""

    name: str
    description: str = ""
    status: GoalStatus = GoalStatus.ACTIVE
    priority: int = 0
