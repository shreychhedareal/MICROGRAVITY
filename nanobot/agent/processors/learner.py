"""Incremental Learner — continuous learning from agent interactions.

Tracks tool proficiency, skill×intent affinity, agent group strategies,
and capability utilisation across all swarm interactions.

Architecture Rationale
─────────────────────
Without feedback-driven learning, the swarm repeats mistakes and
under-utilises available tools.  The learner converts raw interaction
logs into structured insights that feed the routing mapper, speculative
planner, and context builder.

The data structure is append-only counters and rolling averages —
zero ML dependencies, sub-millisecond updates, JSON-serialisable.

Complexity: MEDIUM
Necessity:  HIGH — the intelligence layer's ability to self-improve
            depends entirely on this module's telemetry.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger


class ToolProfile:
    """Usage statistics for a single tool."""

    def __init__(self, name: str):
        self.name = name
        self.call_count = 0
        self.success_count = 0
        self.total_latency_ms = 0.0
        self.common_args: dict[str, int] = defaultdict(int)

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / max(1, self.call_count)

    @property
    def success_rate(self) -> float:
        return self.success_count / max(1, self.call_count)

    def record(self, success: bool, latency_ms: float = 0.0, args: dict[str, Any] | None = None) -> None:
        self.call_count += 1
        if success:
            self.success_count += 1
        self.total_latency_ms += latency_ms
        if args:
            for key in args:
                self.common_args[key] += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "call_count": self.call_count,
            "success_rate": round(self.success_rate, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "top_args": dict(sorted(self.common_args.items(), key=lambda x: -x[1])[:5]),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolProfile:
        tp = cls(data["name"])
        tp.call_count = data.get("call_count", 0)
        tp.success_count = int(data.get("success_rate", 0) * tp.call_count)
        tp.total_latency_ms = data.get("avg_latency_ms", 0) * tp.call_count
        for k, v in data.get("top_args", {}).items():
            tp.common_args[k] = v
        return tp


class IncrementalLearner:
    """Continuously learns from agent interactions.

    Tracks:
    - **Tool profiles**: call count, success rate, latency, common args
    - **Skill affinity**: which skills are invoked for which intent categories
    - **Agent group strategies**: which persona (worker/researcher) works best for each task type
    - **Capability insights**: periodic analysis of utilisation patterns
    """

    def __init__(self, workspace: Path):
        self._path = workspace / "processors" / "learner_state.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._tool_profiles: dict[str, ToolProfile] = {}
        self._skill_affinity: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._agent_strategies: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._total_interactions = 0
        self._load()

    # ── Persistence ────────────────────────────────────────────────

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for td in data.get("tool_profiles", []):
                tp = ToolProfile.from_dict(td)
                self._tool_profiles[tp.name] = tp
            for intent, skills in data.get("skill_affinity", {}).items():
                self._skill_affinity[intent] = defaultdict(int, skills)
            for task_type, personas in data.get("agent_strategies", {}).items():
                self._agent_strategies[task_type] = defaultdict(int, personas)
            self._total_interactions = data.get("total_interactions", 0)
        except Exception as e:
            logger.warning("Learner load error: {}", e)

    def _save(self) -> None:
        payload = {
            "updated_at": datetime.now().isoformat(),
            "total_interactions": self._total_interactions,
            "tool_profiles": [tp.to_dict() for tp in self._tool_profiles.values()],
            "skill_affinity": {k: dict(v) for k, v in self._skill_affinity.items()},
            "agent_strategies": {k: dict(v) for k, v in self._agent_strategies.items()},
        }
        self._path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── Recording API ──────────────────────────────────────────────

    def record_tool_use(
        self,
        tool_name: str,
        success: bool,
        latency_ms: float = 0.0,
        args: dict[str, Any] | None = None,
    ) -> None:
        """Record a tool invocation with its outcome."""
        if tool_name not in self._tool_profiles:
            self._tool_profiles[tool_name] = ToolProfile(tool_name)
        self._tool_profiles[tool_name].record(success, latency_ms, args)
        self._total_interactions += 1
        if self._total_interactions % 10 == 0:
            self._save()

    def record_skill_use(self, intent_category: str, skill_name: str) -> None:
        """Record which skill was used for a given intent type."""
        self._skill_affinity[intent_category][skill_name] += 1

    def record_agent_strategy(
        self,
        task_type: str,
        persona: str,
        success: bool,
    ) -> None:
        """Record which agent persona worked for a task type."""
        key = f"{persona}:{'success' if success else 'fail'}"
        self._agent_strategies[task_type][key] += 1

    # ── Insight Queries ────────────────────────────────────────────

    def get_tool_insights(self) -> list[dict[str, Any]]:
        """Return tool profiles sorted by usage."""
        profiles = sorted(
            self._tool_profiles.values(),
            key=lambda t: -t.call_count,
        )
        return [tp.to_dict() for tp in profiles]

    def get_underused_tools(self, threshold: int = 2) -> list[str]:
        """Return tools that have been used fewer than `threshold` times."""
        return [
            tp.name for tp in self._tool_profiles.values()
            if tp.call_count < threshold
        ]

    def get_failing_tools(self, threshold: float = 0.5) -> list[dict[str, Any]]:
        """Return tools with success rate below threshold."""
        return [
            tp.to_dict() for tp in self._tool_profiles.values()
            if tp.success_rate < threshold and tp.call_count >= 3
        ]

    def best_skill_for_intent(self, intent_category: str) -> str | None:
        """Return the most frequently used skill for an intent type."""
        skills = self._skill_affinity.get(intent_category, {})
        if not skills:
            return None
        return max(skills, key=skills.get)

    def best_persona_for_task(self, task_type: str) -> str | None:
        """Return the persona with the highest success rate for a task type."""
        strategies = self._agent_strategies.get(task_type, {})
        if not strategies:
            return None
        personas: dict[str, dict[str, int]] = {}
        for key, count in strategies.items():
            persona, outcome = key.rsplit(":", 1)
            if persona not in personas:
                personas[persona] = {"success": 0, "fail": 0}
            personas[persona][outcome] = count
        best = max(
            personas.items(),
            key=lambda x: x[1]["success"] / max(1, x[1]["success"] + x[1]["fail"]),
        )
        return best[0]

    # ── Introspection ──────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_interactions": self._total_interactions,
            "tools_tracked": len(self._tool_profiles),
            "intent_categories": len(self._skill_affinity),
            "task_types_tracked": len(self._agent_strategies),
        }

    def render_status(self) -> str:
        s = self.get_stats()
        lines = [
            "=== INCREMENTAL LEARNER STATUS ===",
            f"Interactions: {s['total_interactions']}",
            f"Tools tracked: {s['tools_tracked']}",
            f"Intent categories: {s['intent_categories']}",
            f"Task types: {s['task_types_tracked']}",
        ]
        failing = self.get_failing_tools()
        if failing:
            lines.append("\n⚠ Failing tools:")
            for t in failing[:3]:
                lines.append(f"  {t['name']}: {t['success_rate']:.0%} success ({t['call_count']} calls)")
        return "\n".join(lines)

    def generate_capability_report(self) -> str:
        """Generate a comprehensive capability utilisation report."""
        lines = ["=== CAPABILITY UTILISATION REPORT ===", ""]

        # Tool rankings
        lines.append("--- Tool Rankings (by usage) ---")
        for tp in sorted(self._tool_profiles.values(), key=lambda t: -t.call_count)[:10]:
            lines.append(
                f"  {tp.name}: {tp.call_count} calls, "
                f"{tp.success_rate:.0%} success, "
                f"{tp.avg_latency_ms:.0f}ms avg"
            )

        # Skill affinities
        if self._skill_affinity:
            lines.append("\n--- Skill × Intent Affinity ---")
            for intent, skills in sorted(self._skill_affinity.items()):
                top_skill = max(skills, key=skills.get)
                lines.append(f"  {intent} → {top_skill} ({skills[top_skill]} uses)")

        # Agent strategies
        if self._agent_strategies:
            lines.append("\n--- Agent Group Strategies ---")
            for task_type in sorted(self._agent_strategies):
                best = self.best_persona_for_task(task_type)
                lines.append(f"  {task_type} → best persona: {best}")

        return "\n".join(lines)
