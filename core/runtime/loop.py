"""Runtime Control Loop.

The heart of the system. Runs the tick-based decision loop:
  1. Update world state (simulation tick)
  2. Evaluate FSM mode transition
  3. Select action from current mode
  4. Check constraints
  5. Execute action (or block if constrained)
  6. Record decision trace
  7. Repeat until done or max ticks

See ADR-001: runtime owns control.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from adapters.simulation.grid import GridSimulation
    from core.constraints.engine import ConstraintEngine
    from policies.fsm.agent_fsm import AgentFSM
from core.events.bus import Event, EventBus, EventType
from core.models.actions import Action, ActionType
from core.models.traces import DecisionReason, DecisionTrace


class RuntimeLoop:
    """Top-level control loop for the deterministic agent runtime."""

    def __init__(
        self,
        simulation: GridSimulation,
        constraint_engine: ConstraintEngine,
        fsm: AgentFSM,
        event_bus: EventBus,
        max_ticks: int = 100,
    ) -> None:
        self._sim = simulation
        self._constraints = constraint_engine
        self._fsm = fsm
        self._bus = event_bus
        self._max_ticks = max_ticks
        self._traces: list[DecisionTrace] = []

    @property
    def traces(self) -> list[DecisionTrace]:
        """Decision traces from the run."""
        return list(self._traces)

    def run(self) -> list[DecisionTrace]:
        """Execute the full runtime loop until done or max ticks."""
        for _ in range(self._max_ticks):
            self._sim.tick()
            agent = self._sim.agent
            world = self._sim.world

            # 1. FSM mode transition
            mode = self._fsm.update(agent, world)
            if mode.value == "done":
                break

            # 2. Action selection from FSM
            action = self._fsm.select_action(agent, world)

            # 3. Constraint check (BEFORE execution)
            results = self._constraints.evaluate(action, agent, world)
            violations = [r for r in results if not r.passed]

            if len(violations) > 0:
                # Blocked — record trace with violation, fallback to wait
                trace = DecisionTrace(
                    tick=world.tick,
                    selected_action=Action(
                        action_type=ActionType.WAIT,
                        reason="Blocked by constraints",
                    ),
                    alternatives_considered=[action],
                    reasons=[
                        DecisionReason(
                            stage="constraint",
                            description=v.reason,
                        )
                        for v in violations
                    ],
                    constraints_checked=[r.name for r in results],
                    constraints_violated=[v.name for v in violations],
                )
                self._traces.append(trace)
                self._sim.execute_action(
                    Action(action_type=ActionType.WAIT, reason="Constraint fallback")
                )
                continue

            # 4. Execute action
            self._sim.execute_action(action)

            # 5. Record decision trace
            trace = DecisionTrace(
                tick=world.tick,
                selected_action=action,
                reasons=[
                    DecisionReason(
                        stage="fsm",
                        description=f"Mode={mode.value}, action={action.action_type.value}",
                    ),
                ],
                constraints_checked=[r.name for r in results],
            )
            self._traces.append(trace)
            self._bus.emit(Event(
                event_type=EventType.DECISION_MADE,
                tick=world.tick,
                data={
                    "mode": mode.value,
                    "action": action.action_type.value,
                },
            ))

        return self._traces
