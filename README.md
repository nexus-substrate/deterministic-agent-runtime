# Deterministic Agent Runtime

A production-grade, event-driven programmable agent runtime where **the runtime owns execution control, not the LLM**.

Companion project to [nexus-agents](https://github.com/nexus-substrate/nexus-agents).

## Core Principles

1. **Deterministic first** — explicit state machines, behavior trees, and utility scoring before any model involvement
2. **Replayable** — every run produces decision traces that can be replayed and inspected
3. **Typed everything** — state, events, actions, goals, anomalies, traces — all typed
4. **Bounded LLM** — model advises, runtime decides. LLM cannot bypass constraints or manage state
5. **Observable** — every decision is traceable, every action is logged, every policy is testable

## Architecture

```
Constraints → Interrupts → FSM/BT → Utility → Planner → LLM Advisory → Escalation
     ↑                                                         ↓
     └─────────────── Event Bus ◄──── Executor ◄──── Replay ──┘
```

## Status

**Working vertical slice** — Phases 1-3 complete with 60 passing tests covering the event bus, constraints, FSM, runtime loop, replay, and eval harness.

## Getting Started

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type check
mypy .

# Lint
ruff check .
```

## Project Structure

```
core/          — typed models, events, state, constraints, runtime loop
policies/      — FSM, behavior trees, utility scoring, planner, recovery
adapters/      — simulation environment, external integrations
executor/      — action execution with timeout, retry, fallback
telemetry/     — structured logging and metrics
replay/        — decision trace persistence and replay
plugins/       — narrow SDK and built-in plugins
llm/           — bounded advisory layer (after deterministic core works)
eval/          — seeded scenarios, regression, adversarial tests
console/       — CLI inspection and replay tooling
```

## Standards

This project follows [nexus-agents CODING_STANDARDS.md](https://github.com/nexus-substrate/nexus-agents/blob/main/CODING_STANDARDS.md).

See [AGENTS.md](./AGENTS.md) for non-negotiable architectural rules.

## License

MIT
