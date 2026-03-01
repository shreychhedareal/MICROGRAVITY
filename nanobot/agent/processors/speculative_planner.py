"""Speculative Action Planner — predictive pre-fetching for the agent loop.

Analyzes recent tool call sequences via a Markov transition model and
speculatively pre-fetches data for predicted next actions.

Architecture Rationale
─────────────────────
Agent loops are inherently sequential: call tool → wait → process →
call next tool.  By predicting the next tool call with >70% confidence,
we can overlap the wait for the current call with pre-fetching for
the next one.  This converts serial latency into parallel I/O.

The Markov model is lightweight (dict of dicts) and learns online from
every tool invocation.  No external ML dependency required.

Complexity: MEDIUM
Necessity:  MEDIUM — biggest impact on multi-step file/web workflows
            where each step has a predictable successor.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger


class ToolTransitionModel:
    """First-order Markov model over tool call sequences.

    Tracks how often tool B follows tool A and computes transition
    probabilities.  Used to predict the next tool call.
    """

    def __init__(self):
        # transitions[from_tool][to_tool] = count
        self._transitions: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._total_from: dict[str, int] = defaultdict(int)

    def observe(self, from_tool: str, to_tool: str) -> None:
        """Record an observed transition."""
        self._transitions[from_tool][to_tool] += 1
        self._total_from[from_tool] += 1

    def predict(self, current_tool: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Predict the next tool(s) with confidence scores.

        Returns:
            List of {tool, confidence} dicts sorted by confidence desc.
        """
        if current_tool not in self._transitions:
            return []

        total = self._total_from[current_tool]
        if total == 0:
            return []

        predictions = []
        for tool, count in self._transitions[current_tool].items():
            confidence = count / total
            predictions.append({"tool": tool, "confidence": round(confidence, 3)})

        predictions.sort(key=lambda x: -x["confidence"])
        return predictions[:top_k]

    def to_dict(self) -> dict[str, Any]:
        return {
            "transitions": {k: dict(v) for k, v in self._transitions.items()},
            "total_from": dict(self._total_from),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolTransitionModel:
        model = cls()
        for from_tool, targets in data.get("transitions", {}).items():
            for to_tool, count in targets.items():
                model._transitions[from_tool][to_tool] = count
                model._total_from[from_tool] += count
        return model


class Prediction:
    """A single speculative prediction with its pre-fetch result."""

    def __init__(self, tool: str, confidence: float, context: dict[str, Any] | None = None):
        self.tool = tool
        self.confidence = confidence
        self.context = context or {}
        self.prefetched_data: Any = None
        self.was_correct: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "confidence": self.confidence,
            "was_correct": self.was_correct,
            "has_prefetched": self.prefetched_data is not None,
        }


class SpeculativePlanner:
    """Predicts next agent actions and optionally pre-fetches data.

    Integrates with the agent loop to:
    1. Record every tool call transition
    2. After each call, predict the next 1-3 tools
    3. For high-confidence predictions, trigger pre-fetching

    The prediction model is persisted to disk and loaded on startup.
    """

    def __init__(
        self,
        workspace: Path,
        confidence_threshold: float = 0.7,
    ):
        self._workspace = workspace
        self._model_path = workspace / "processors" / "tool_transitions.json"
        self._model_path.parent.mkdir(parents=True, exist_ok=True)
        self._threshold = confidence_threshold
        self._model = self._load_model()
        self._last_tool: str | None = None
        self._active_predictions: list[Prediction] = []
        self._stats = {"predictions_made": 0, "predictions_correct": 0, "prefetches_triggered": 0}

    # ── Persistence ────────────────────────────────────────────────

    def _load_model(self) -> ToolTransitionModel:
        if self._model_path.exists():
            try:
                data = json.loads(self._model_path.read_text(encoding="utf-8"))
                return ToolTransitionModel.from_dict(data)
            except Exception:
                pass
        return ToolTransitionModel()

    def _save_model(self) -> None:
        payload = {
            "updated_at": datetime.now().isoformat(),
            "model": self._model.to_dict(),
        }
        self._model_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── Core API ───────────────────────────────────────────────────

    def on_tool_called(self, tool_name: str) -> list[Prediction]:
        """Record a tool call and produce predictions for the next action.

        Call this after every tool execution in the agent loop.
        Returns high-confidence predictions that could be pre-fetched.
        """
        # Record transition
        if self._last_tool:
            self._model.observe(self._last_tool, tool_name)

        # Evaluate previous predictions
        for pred in self._active_predictions:
            pred.was_correct = (pred.tool == tool_name)
            if pred.was_correct:
                self._stats["predictions_correct"] += 1

        self._last_tool = tool_name

        # Generate new predictions
        raw_preds = self._model.predict(tool_name)
        self._active_predictions = []

        for p in raw_preds:
            if p["confidence"] >= self._threshold:
                pred = Prediction(tool=p["tool"], confidence=p["confidence"])
                self._active_predictions.append(pred)
                self._stats["predictions_made"] += 1

        # Periodically persist
        if self._stats["predictions_made"] % 20 == 0 and self._stats["predictions_made"] > 0:
            self._save_model()

        return self._active_predictions

    def get_active_predictions(self) -> list[Prediction]:
        """Return current high-confidence predictions."""
        return self._active_predictions

    def mark_prefetched(self, tool_name: str, data: Any) -> None:
        """Attach pre-fetched data to a prediction."""
        for pred in self._active_predictions:
            if pred.tool == tool_name:
                pred.prefetched_data = data
                self._stats["prefetches_triggered"] += 1
                break

    def get_prefetched(self, tool_name: str) -> Any:
        """Retrieve pre-fetched data if available."""
        for pred in self._active_predictions:
            if pred.tool == tool_name and pred.prefetched_data is not None:
                return pred.prefetched_data
        return None

    def reset_session(self) -> None:
        """Reset the session state (keep the learned model)."""
        self._last_tool = None
        self._active_predictions = []
        self._save_model()

    # ── Introspection ──────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        accuracy = 0.0
        if self._stats["predictions_made"] > 0:
            accuracy = self._stats["predictions_correct"] / self._stats["predictions_made"]
        return {
            **self._stats,
            "accuracy": round(accuracy, 3),
            "model_transitions": len(self._model._transitions),
        }

    def render_status(self) -> str:
        s = self.get_stats()
        lines = [
            "=== SPECULATIVE PLANNER STATUS ===",
            f"Predictions: {s['predictions_made']}  Correct: {s['predictions_correct']}",
            f"Accuracy: {s['accuracy']:.1%}",
            f"Prefetches triggered: {s['prefetches_triggered']}",
            f"Learned transitions: {s['model_transitions']} tools",
        ]
        if self._active_predictions:
            lines.append("\nActive predictions:")
            for p in self._active_predictions:
                lines.append(f"  → {p.tool} (confidence: {p.confidence:.1%})")
        return "\n".join(lines)
