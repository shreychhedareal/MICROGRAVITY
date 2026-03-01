"""Architecture Knowledge Base — machine-readable rationale graph.

Documents why each component exists, what breaks without it, and how
modules depend on each other.  Queryable by the agent itself when
asked "why does X work this way?"

Architecture Rationale
─────────────────────
Complex architectures become unmaintainable without embedded rationale.
This module ensures the swarm can EXPLAIN ITSELF — to the developer,
to the user, and to other agents.  The knowledge graph also powers
auto-generated connectionism reports showing inter-module dependencies.

Complexity: LOW-MEDIUM (data structure is simple, value is enormous)
Necessity:  CRITICAL — the most sophisticated architecture is useless
            if nobody (human or agent) understands why it exists.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger


class ComponentEntry:
    """A single entry in the architecture knowledge graph."""

    def __init__(
        self,
        name: str,
        module_path: str,
        purpose: str,
        rationale: str,
        complexity: str = "medium",
        necessity: str = "high",
        breaks_without: str = "",
        depends_on: list[str] | None = None,
        depended_by: list[str] | None = None,
        sensitivities: list[str] | None = None,
        insights: list[str] | None = None,
    ):
        self.name = name
        self.module_path = module_path
        self.purpose = purpose
        self.rationale = rationale
        self.complexity = complexity
        self.necessity = necessity
        self.breaks_without = breaks_without
        self.depends_on: list[str] = depends_on or []
        self.depended_by: list[str] = depended_by or []
        self.sensitivities: list[str] = sensitivities or []
        self.insights: list[str] = insights or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "module_path": self.module_path,
            "purpose": self.purpose,
            "rationale": self.rationale,
            "complexity": self.complexity,
            "necessity": self.necessity,
            "breaks_without": self.breaks_without,
            "depends_on": self.depends_on,
            "depended_by": self.depended_by,
            "sensitivities": self.sensitivities,
            "insights": self.insights,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComponentEntry:
        return cls(**{k: v for k, v in data.items() if k in cls.__init__.__code__.co_varnames})


class ArchitectureKnowledgeBase:
    """Queryable knowledge graph of architecture components.

    Each component is documented with:
    - Purpose: what it does
    - Rationale: why it exists
    - Breaks without: what fails if removed
    - Dependencies: upstream and downstream
    - Sensitivities: parameters or conditions it's sensitive to
    - Insights: accumulated observations about its behaviour
    """

    def __init__(self, workspace: Path):
        self._path = workspace / "processors" / "arch_knowledge.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._components: dict[str, ComponentEntry] = {}
        self._load()
        if not self._components:
            self._seed_defaults()

    # ── Persistence ────────────────────────────────────────────────

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for entry in data.get("components", []):
                comp = ComponentEntry.from_dict(entry)
                self._components[comp.name] = comp
        except Exception as e:
            logger.warning("ArchKB load error: {}", e)

    def _save(self) -> None:
        payload = {
            "version": 1,
            "updated_at": datetime.now().isoformat(),
            "components": [c.to_dict() for c in self._components.values()],
        }
        self._path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _seed_defaults(self) -> None:
        """Seed the knowledge base with the core architecture components."""
        defaults = [
            ComponentEntry(
                name="IntelligentCache",
                module_path="processors/cache.py",
                purpose="LRU + semantic-similarity cache to avoid redundant LLM calls",
                rationale="LLM calls cost tokens and latency. A 30% cache hit rate saves significant budget.",
                complexity="medium", necessity="high",
                breaks_without="Every query hits the LLM, increasing cost and latency by 30-50%",
                depends_on=["VectorMemory"],
                depended_by=["AgentLoop"],
                sensitivities=["TTL too short → low hit rate", "TTL too long → stale results"],
            ),
            ComponentEntry(
                name="BulkIOProcessor",
                module_path="processors/bulk_io.py",
                purpose="Batch LMDB reads/writes for throughput",
                rationale="LMDB single-writer lock makes individual txns expensive. Batching yields 10-50× improvement.",
                complexity="low", necessity="high",
                breaks_without="Concurrent subagent writes serialize and bottleneck",
                depends_on=["VectorMemory"],
                depended_by=["MemoryStore", "TaskTree"],
            ),
            ComponentEntry(
                name="SpeculativePlanner",
                module_path="processors/speculative_planner.py",
                purpose="Markov-chain prediction of next tool call for pre-fetching",
                rationale="Agent loops are sequential. Overlapping wait time with I/O reduces perceived latency.",
                complexity="medium", necessity="medium",
                breaks_without="No pre-fetching; each tool call waits serially for data",
                depends_on=["IncrementalLearner"],
                depended_by=["AgentLoop"],
                sensitivities=["Low accuracy wastes I/O on wrong pre-fetches"],
            ),
            ComponentEntry(
                name="RoutingMapper",
                module_path="processors/routing.py",
                purpose="Learned query→agent/skill dispatch table",
                rationale="Eliminates LLM token waste on re-discovering tool mappings for repeated query types.",
                complexity="medium", necessity="high",
                breaks_without="Intent routing falls back to LLM each time, wasting tokens",
                depends_on=["IncrementalLearner", "VectorMemory"],
                depended_by=["IntentAnalyzer", "AgentLoop"],
            ),
            ComponentEntry(
                name="IncrementalLearner",
                module_path="processors/learner.py",
                purpose="Continuous learning from agent interactions",
                rationale="Raw interaction logs are useless without structured insights. This converts telemetry into actionable intelligence.",
                complexity="medium", necessity="high",
                breaks_without="Routing mapper and speculative planner have no data to learn from",
                depends_on=[],
                depended_by=["RoutingMapper", "SpeculativePlanner", "AwarenessProjector"],
            ),
            ComponentEntry(
                name="AwarenessProjector",
                module_path="processors/awareness.py",
                purpose="Structured self/swarm state model with seeker→controller projection",
                rationale="Agents must reason about their limitations to delegate efficiently. Without this, they either over-request or silently fail.",
                complexity="high", necessity="high",
                breaks_without="Agents cannot reason about delegation; subagents get stuck without escalation",
                depends_on=["IncrementalLearner", "SubagentManager"],
                depended_by=["ContextBuilder", "AgentLoop"],
                sensitivities=["Stale snapshots cause wrong delegation decisions"],
            ),
            ComponentEntry(
                name="ArchitectureKnowledgeBase",
                module_path="processors/arch_knowledge.py",
                purpose="Machine-readable rationale graph for the architecture",
                rationale="Complex architectures become unmaintainable without embedded rationale. This module ensures the swarm can explain itself.",
                complexity="low", necessity="critical",
                breaks_without="Nobody understands why the system works the way it does",
                depends_on=[],
                depended_by=["All agents via introspection"],
                insights=["The most sophisticated architecture is useless if nobody understands why it exists"],
            ),
            ComponentEntry(
                name="TaskTree",
                module_path="agent/task_tree.py",
                purpose="DAG-based task dependency tracking with checkpoints",
                rationale="Multi-step workflows need dependency ordering. Without a DAG, tasks execute in wrong order.",
                complexity="medium", necessity="high",
                breaks_without="Dependent tasks start before prerequisites complete, causing cascading failures",
                depends_on=["MemoryStore"],
                depended_by=["Scheduler", "AgentLoop"],
            ),
            ComponentEntry(
                name="Scheduler",
                module_path="agent/scheduler.py",
                purpose="Unified trigger dispatcher for event and consequence-driven actions",
                rationale="Reactive triggers enable autonomous operation without polling. The swarm responds to changes rather than waiting for commands.",
                complexity="medium", necessity="medium",
                breaks_without="No reactive automation; all actions require explicit user commands",
                depends_on=["TaskTree", "VectorMemory"],
                depended_by=["AgentLoop", "SubagentManager"],
            ),
        ]
        for comp in defaults:
            self._components[comp.name] = comp
        self._save()

    # ── CRUD ───────────────────────────────────────────────────────

    def register_component(self, entry: ComponentEntry) -> None:
        self._components[entry.name] = entry
        self._save()

    def get_component(self, name: str) -> ComponentEntry | None:
        return self._components.get(name)

    def add_insight(self, component_name: str, insight: str) -> bool:
        comp = self._components.get(component_name)
        if not comp:
            return False
        comp.insights.append(insight)
        self._save()
        return True

    # ── Queries ────────────────────────────────────────────────────

    def explain(self, component_name: str) -> str:
        """Human-readable explanation of a component."""
        comp = self._components.get(component_name)
        if not comp:
            return f"Component '{component_name}' not found in the knowledge base."
        lines = [
            f"## {comp.name}",
            f"**Module**: `{comp.module_path}`",
            f"**Purpose**: {comp.purpose}",
            f"**Rationale**: {comp.rationale}",
            f"**Complexity**: {comp.complexity} | **Necessity**: {comp.necessity}",
            f"**Breaks without**: {comp.breaks_without}",
        ]
        if comp.depends_on:
            lines.append(f"**Depends on**: {', '.join(comp.depends_on)}")
        if comp.depended_by:
            lines.append(f"**Depended by**: {', '.join(comp.depended_by)}")
        if comp.sensitivities:
            lines.append("**Sensitivities**:")
            for s in comp.sensitivities:
                lines.append(f"  - {s}")
        if comp.insights:
            lines.append("**Insights**:")
            for i in comp.insights[:5]:
                lines.append(f"  - {i}")
        return "\n".join(lines)

    def get_dependency_graph(self) -> dict[str, list[str]]:
        """Return the full dependency adjacency list."""
        return {
            name: comp.depends_on
            for name, comp in self._components.items()
        }

    def get_critical_path(self) -> list[str]:
        """Return components marked as critical necessity."""
        return [c.name for c in self._components.values() if c.necessity == "critical"]

    # ── Reports ────────────────────────────────────────────────────

    def generate_connectionism_report(self) -> str:
        """Generate an inter-module dependency/rationale report."""
        lines = ["=== ARCHITECTURE CONNECTIONISM REPORT ===", ""]

        for comp in self._components.values():
            lines.append(f"[{comp.complexity.upper()}] {comp.name}")
            lines.append(f"  Why: {comp.rationale[:80]}")
            if comp.depends_on:
                lines.append(f"  ← Needs: {', '.join(comp.depends_on)}")
            if comp.depended_by:
                lines.append(f"  → Powers: {', '.join(comp.depended_by)}")
            lines.append("")

        # Critical path
        critical = self.get_critical_path()
        if critical:
            lines.append(f"CRITICAL COMPONENTS: {', '.join(critical)}")

        return "\n".join(lines)

    def render_status(self) -> str:
        return (
            f"=== ARCHITECTURE KB STATUS ===\n"
            f"Components documented: {len(self._components)}\n"
            f"Critical: {len(self.get_critical_path())}\n"
            f"Dependency edges: {sum(len(c.depends_on) for c in self._components.values())}"
        )
