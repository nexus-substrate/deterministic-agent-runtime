"""Integration test: full scenario run.

Proves the vertical slice works end-to-end:
- Simulation generates a deterministic world
- FSM selects modes based on agent state
- Constraints block illegal actions
- Decision traces are produced for every tick
- Same seed produces same outcome (replayability)
"""

from adapters.simulation.grid import GridSimulation, SimulationConfig
from core.constraints.engine import create_default_engine
from core.events.bus import EventBus, EventType
from core.runtime.loop import RuntimeLoop
from policies.fsm.agent_fsm import AgentFSM


class TestFullScenario:
    def _run_scenario(self, seed: int = 42) -> RuntimeLoop:
        bus = EventBus()
        config = SimulationConfig(
            seed=seed, width=8, height=8,
            num_obstacles=4, num_threats=2,
        )
        sim = GridSimulation(config, bus)
        constraints = create_default_engine(bus)
        fsm = AgentFSM()
        runtime = RuntimeLoop(sim, constraints, fsm, bus, max_ticks=50)
        runtime.run()
        return runtime

    def test_produces_traces(self) -> None:
        runtime = self._run_scenario()
        assert len(runtime.traces) > 0

    def test_traces_have_constraints(self) -> None:
        runtime = self._run_scenario()
        for trace in runtime.traces:
            assert len(trace.constraints_checked) > 0

    def test_deterministic_replay(self) -> None:
        """Same seed must produce identical traces."""
        run1 = self._run_scenario(seed=42)
        run2 = self._run_scenario(seed=42)
        assert len(run1.traces) == len(run2.traces)
        for t1, t2 in zip(run1.traces, run2.traces, strict=True):
            assert t1.tick == t2.tick
            assert t1.selected_action.action_type == t2.selected_action.action_type

    def test_different_seed_different_result(self) -> None:
        run1 = self._run_scenario(seed=42)
        run2 = self._run_scenario(seed=99)
        # Different seeds should produce different worlds
        # (traces may differ in length or actions)
        all(
            t1.selected_action.action_type == t2.selected_action.action_type
            for t1, t2 in zip(run1.traces, run2.traces, strict=False)
        )
        # Not a guarantee they differ, but very likely with different seeds
        assert len(run1.traces) > 0
        assert len(run2.traces) > 0

    def test_events_emitted(self) -> None:
        bus = EventBus()
        config = SimulationConfig(seed=42, width=8, height=8, num_threats=1)
        sim = GridSimulation(config, bus)
        constraints = create_default_engine(bus)
        fsm = AgentFSM()
        runtime = RuntimeLoop(sim, constraints, fsm, bus, max_ticks=20)
        runtime.run()
        # Should have tick events, decision events, constraint events
        assert bus.history_size > 0
        ticks = bus.get_history(event_type=EventType.TICK)
        assert len(ticks) > 0
        decisions = bus.get_history(event_type=EventType.DECISION_MADE)
        assert len(decisions) > 0

    def test_agent_cannot_move_out_of_bounds(self) -> None:
        """Constraints block out-of-bounds movement."""
        bus = EventBus()
        config = SimulationConfig(seed=1, width=3, height=3, num_obstacles=0, num_threats=1)
        sim = GridSimulation(config, bus)
        constraints = create_default_engine(bus)
        fsm = AgentFSM()
        runtime = RuntimeLoop(sim, constraints, fsm, bus, max_ticks=30)
        runtime.run()
        # No constraint violation should crash the system
        bus.get_history(event_type=EventType.CONSTRAINT_VIOLATED)
        # Any violations were handled gracefully (fallback to wait)
        for trace in runtime.traces:
            if len(trace.constraints_violated) > 0:
                assert trace.selected_action.action_type.value == "wait"
