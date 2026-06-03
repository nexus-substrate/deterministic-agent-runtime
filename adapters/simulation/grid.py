"""Deterministic Grid Simulation.

A simple bounded grid world where an agent navigates obstacles,
avoids threats, and manages resources. All randomness is seeded
for perfect reproducibility.

Phase 2 deliverable — the first scenario that proves the architecture.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import ClassVar

from core.events.bus import Event, EventBus, EventType
from core.models.actions import Action, ActionResult, ActionType
from core.models.state import AgentState, Position, WorldState


@dataclass
class SimulationConfig:
    """Configuration for the grid simulation."""

    width: int = 10
    height: int = 10
    seed: int = 42
    num_obstacles: int = 8
    num_threats: int = 3
    threat_damage: int = 20
    move_cost: int = 5
    attack_cost: int = 15
    scan_cost: int = 10


class GridSimulation:
    """Deterministic grid simulation adapter.

    The simulation is the environment — it owns world state
    and processes action results. It does NOT make decisions
    (that's the runtime's job).
    """

    def __init__(self, config: SimulationConfig, event_bus: EventBus) -> None:
        self._config = config
        self._bus = event_bus
        self._rng = random.Random(config.seed)
        self._world = self._generate_world()
        self._agent = AgentState(position=Position(x=0, y=0))

    @property
    def world(self) -> WorldState:
        """Current world state (read-only view)."""
        return self._world

    @property
    def agent(self) -> AgentState:
        """Current agent state (read-only view)."""
        return self._agent

    def tick(self) -> None:
        """Advance simulation by one tick."""
        self._world = self._world.model_copy(update={"tick": self._world.tick + 1})
        self._bus.emit(Event(
            event_type=EventType.TICK,
            tick=self._world.tick,
        ))

    def execute_action(self, action: Action) -> ActionResult:
        """Execute an action and return the result.

        This is a pure environment response — no decision logic here.
        """
        handler = self._action_handlers.get(action.action_type)
        if handler is None:
            return ActionResult(
                action=action, success=False,
                message=f"Unknown action: {action.action_type}",
                tick=self._world.tick,
            )
        result = handler(self, action)
        self._bus.emit(Event(
            event_type=EventType.AGENT_ACTED,
            tick=self._world.tick,
            data={"action": action.action_type.value, "success": result.success},
        ))
        return result

    def _handle_move(self, action: Action) -> ActionResult:
        if action.target is None:
            return ActionResult(
                action=action, success=False,
                message="Move requires target", tick=self._world.tick,
            )
        self._agent = self._agent.model_copy(update={
            "position": action.target,
            "energy": max(0, self._agent.energy - self._config.move_cost),
        })
        self._bus.emit(Event(
            event_type=EventType.AGENT_MOVED,
            tick=self._world.tick,
            data={"x": action.target.x, "y": action.target.y},
        ))
        # Check threat damage
        if action.target in self._world.threats:
            damage = self._config.threat_damage
            new_health = max(0, self._agent.health - damage)
            self._agent = self._agent.model_copy(update={
                "health": new_health,
                "alive": new_health > 0,
            })
            self._bus.emit(Event(
                event_type=EventType.AGENT_DAMAGED,
                tick=self._world.tick,
                data={"damage": damage, "health": new_health},
            ))
            if not self._agent.alive:
                self._bus.emit(Event(
                    event_type=EventType.AGENT_DIED,
                    tick=self._world.tick,
                ))
        return ActionResult(
            action=action, success=True,
            message="Moved", energy_cost=self._config.move_cost,
            tick=self._world.tick,
        )

    def _handle_wait(self, action: Action) -> ActionResult:
        # Waiting recovers 5 energy
        self._agent = self._agent.model_copy(update={
            "energy": min(100, self._agent.energy + 5),
        })
        return ActionResult(
            action=action, success=True,
            message="Waited", energy_cost=0, tick=self._world.tick,
        )

    def _handle_attack(self, action: Action) -> ActionResult:
        self._agent = self._agent.model_copy(update={
            "energy": max(0, self._agent.energy - self._config.attack_cost),
        })
        # Remove threat at target if present
        if action.target is not None and action.target in self._world.threats:
            new_threats = [t for t in self._world.threats if t != action.target]
            self._world = self._world.model_copy(update={"threats": new_threats})
            return ActionResult(
                action=action, success=True,
                message="Threat eliminated",
                energy_cost=self._config.attack_cost, tick=self._world.tick,
            )
        return ActionResult(
            action=action, success=False,
            message="No threat at target",
            energy_cost=self._config.attack_cost, tick=self._world.tick,
        )

    def _handle_scan(self, action: Action) -> ActionResult:
        self._agent = self._agent.model_copy(update={
            "energy": max(0, self._agent.energy - self._config.scan_cost),
        })
        return ActionResult(
            action=action, success=True,
            message=f"Scanned: {len(self._world.threats)} threats visible",
            energy_cost=self._config.scan_cost, tick=self._world.tick,
        )

    def _handle_retreat(self, action: Action) -> ActionResult:
        # Retreat to origin
        self._agent = self._agent.model_copy(update={
            "position": Position(x=0, y=0),
            "energy": max(0, self._agent.energy - self._config.move_cost),
        })
        return ActionResult(
            action=action, success=True,
            message="Retreated to origin",
            energy_cost=self._config.move_cost, tick=self._world.tick,
        )

    _action_handlers: ClassVar[dict[ActionType, object]] = {
        ActionType.MOVE: _handle_move,
        ActionType.WAIT: _handle_wait,
        ActionType.ATTACK: _handle_attack,
        ActionType.SCAN: _handle_scan,
        ActionType.RETREAT: _handle_retreat,
    }

    def _generate_world(self) -> WorldState:
        """Generate a deterministic world from the seeded RNG."""
        obstacles: list[Position] = []
        threats: list[Position] = []
        occupied = {(0, 0)}  # Reserve agent start position

        for _ in range(self._config.num_obstacles):
            pos = self._random_free_position(occupied)
            obstacles.append(pos)
            occupied.add((pos.x, pos.y))

        for _ in range(self._config.num_threats):
            pos = self._random_free_position(occupied)
            threats.append(pos)
            occupied.add((pos.x, pos.y))

        return WorldState(
            width=self._config.width,
            height=self._config.height,
            obstacles=obstacles,
            threats=threats,
        )

    def _random_free_position(self, occupied: set[tuple[int, int]]) -> Position:
        """Generate a random position not in the occupied set."""
        while True:
            x = self._rng.randint(0, self._config.width - 1)
            y = self._rng.randint(0, self._config.height - 1)
            if (x, y) not in occupied:
                return Position(x=x, y=y)
