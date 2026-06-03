"""Replay Trace Log — Decision trace persistence and replay.

Persists decision traces to JSONL files for replay and inspection.
Replay is a first-class feature, not an afterthought.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from core.models.traces import DecisionTrace


class TraceLog:
    """Persists and reads decision traces from JSONL files."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def write(self, traces: list[DecisionTrace]) -> None:
        """Write traces to a JSONL file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            for trace in traces:
                data = trace.model_dump(mode="json")
                f.write(json.dumps(data) + "\n")

    def read(self) -> list[DecisionTrace]:
        """Read traces from a JSONL file."""
        if not self._path.exists():
            return []
        traces: list[DecisionTrace] = []
        with open(self._path) as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    data = json.loads(stripped)
                    traces.append(DecisionTrace.model_validate(data))
        return traces

    def compare(
        self, run_a: list[DecisionTrace], run_b: list[DecisionTrace]
    ) -> list[dict[str, object]]:
        """Compare two runs and return divergences."""
        divergences: list[dict[str, object]] = []
        max_len = max(len(run_a), len(run_b))
        for i in range(max_len):
            a = run_a[i] if i < len(run_a) else None
            b = run_b[i] if i < len(run_b) else None
            if a is None or b is None:
                divergences.append({
                    "index": i,
                    "reason": "Run length mismatch",
                    "a": a.selected_action.action_type.value if a else None,
                    "b": b.selected_action.action_type.value if b else None,
                })
            elif a.selected_action.action_type != b.selected_action.action_type:
                divergences.append({
                    "index": i,
                    "tick_a": a.tick,
                    "tick_b": b.tick,
                    "reason": "Action mismatch",
                    "a": a.selected_action.action_type.value,
                    "b": b.selected_action.action_type.value,
                })
        return divergences
