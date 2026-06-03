"""Agent FSM — Top-Level Mode Selection.

Deterministic state machine for agent behavior modes.
The FSM selects the current mode; action selection within
each mode uses utility scoring or simple heuristics.

See ADR-001: FSM for top-level modes, behavior trees only
where they provide clear intra-mode value.
"""

from __future__ import annotations

from enum import StrEnum

from core.models.actions import Action, ActionType
from core.models.state import AgentState, Position, WorldState


class AgentMode(StrEnum):
    """Top-level agent behavior modes."""

    EXPLORE = "explore"
    ENGAGE = "engage"
    RETREAT = "retreat"
    HOLD = "hold"
    DONE = "done"


# Thresholds for mode transitions
RETREAT_HEALTH = 25
RETREAT_ENERGY = 10
ENGAGE_RANGE = 3


class AgentFSM:
    """Deterministic finite state machine for agent mode selection.

    Transition rules are explicit and testable. No hidden logic.
    """

    def __init__(self) -> None:
        self._mode = AgentMode.EXPLORE

    @property
    def mode(self) -> AgentMode:
        """Current agent mode."""
        return self._mode

    def update(self, agent: AgentState, world: WorldState) -> AgentMode:
        """Evaluate transitions and return the new mode.

        Transition priority (highest first):
        1. Dead → DONE
        2. Low health/energy → RETREAT
        3. Threat nearby → ENGAGE
        4. No threats left → DONE
        5. Otherwise → EXPLORE
        """
        if not agent.alive:
            self._mode = AgentMode.DONE
            return self._mode

        if agent.health <= RETREAT_HEALTH or agent.energy <= RETREAT_ENERGY:
            self._mode = AgentMode.RETREAT
            return self._mode

        if len(world.threats) == 0:
            self._mode = AgentMode.DONE
            return self._mode

        nearest = self._nearest_threat(agent.position, world)
        if nearest is not None and self._distance(agent.position, nearest) <= ENGAGE_RANGE:
            self._mode = AgentMode.ENGAGE
            return self._mode

        self._mode = AgentMode.EXPLORE
        return self._mode

    def select_action(self, agent: AgentState, world: WorldState) -> Action:
        """Select an action based on current mode.

        Simple heuristic action selection per mode.
        """
        if self._mode == AgentMode.RETREAT:
            return Action(action_type=ActionType.RETREAT, reason="Low health/energy")

        if self._mode == AgentMode.ENGAGE:
            nearest = self._nearest_threat(agent.position, world)
            if nearest is not None:
                dist = self._distance(agent.position, nearest)
                if dist <= 1:
                    return Action(
                        action_type=ActionType.ATTACK,
                        target=nearest,
                        reason="Threat adjacent",
                    )
                return Action(
                    action_type=ActionType.MOVE,
                    target=self._step_toward(agent.position, nearest, world),
                    reason="Moving toward threat",
                )

        if self._mode == AgentMode.EXPLORE:
            nearest = self._nearest_threat(agent.position, world)
            if nearest is not None:
                return Action(
                    action_type=ActionType.MOVE,
                    target=self._step_toward(agent.position, nearest, world),
                    reason="Exploring toward threat",
                )

        if self._mode == AgentMode.DONE:
            return Action(action_type=ActionType.WAIT, reason="Mission complete")

        return Action(action_type=ActionType.WAIT, reason="No action available")

    @staticmethod
    def _distance(a: Position, b: Position) -> int:
        """Manhattan distance."""
        return abs(a.x - b.x) + abs(a.y - b.y)

    @staticmethod
    def _nearest_threat(pos: Position, world: WorldState) -> Position | None:
        """Find the nearest threat by Manhattan distance."""
        if len(world.threats) == 0:
            return None
        return min(world.threats, key=lambda t: abs(t.x - pos.x) + abs(t.y - pos.y))

    @staticmethod
    def _step_toward(
        current: Position, target: Position, world: WorldState
    ) -> Position:
        """Take one step toward target, avoiding obstacles."""
        dx = 0 if target.x == current.x else (1 if target.x > current.x else -1)
        dy = 0 if target.y == current.y else (1 if target.y > current.y else -1)

        # Try x-step first, then y-step, then stay
        candidates = [
            Position(x=current.x + dx, y=current.y) if dx != 0 else None,
            Position(x=current.x, y=current.y + dy) if dy != 0 else None,
        ]
        for c in candidates:
            if c is not None and c not in world.obstacles:
                return c
        return current  # Stuck
