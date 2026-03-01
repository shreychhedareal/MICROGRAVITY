"""Agent Awareness Projector — structured self/swarm state model.

Provides every agent with a machine-readable snapshot of:
- Its own capabilities, loaded skills, active tools, error rates
- Other agents' tasks, progress, and estimated completion
- Seeker→Controller projection for cross-agent information requests

Architecture Rationale
─────────────────────
True autonomy requires agents to reason about their own limitations.
Without projected awareness, agents either:
  (a) over-request help from the controller (flooding the bus), or
  (b) silently fail tasks they could delegate.

The awareness snapshot is a lightweight dict injected into the context
tree on every iteration, consuming ~200 tokens but saving full
re-planning cycles when the agent knows what it can and cannot do.

Complexity: HIGH
Sensitivity: This module is load-bearing for multi-agent coordination.
             If the snapshot is stale or inaccurate, agents make wrong
             delegation decisions.  The refresh interval must balance
             freshness against computation cost.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger


class SelfAwareness:
    """Model of a single agent's own state."""

    def __init__(self):
        self.active_tools: list[str] = []
        self.loaded_skills: list[str] = []
        self.recent_errors: list[dict[str, str]] = []
        self.memory_labels: list[str] = []
        self.current_task: str | None = None
        self.loop_iteration: int = 0
        self.token_budget_remaining: int | None = None

    def update(
        self,
        tools: list[str] | None = None,
        skills: list[str] | None = None,
        current_task: str | None = None,
        loop_iteration: int = 0,
    ) -> None:
        if tools is not None:
            self.active_tools = tools
        if skills is not None:
            self.loaded_skills = skills
        self.current_task = current_task
        self.loop_iteration = loop_iteration

    def record_error(self, tool: str, error: str) -> None:
        self.recent_errors.append({
            "tool": tool,
            "error": error[:200],
            "timestamp": datetime.now().isoformat(),
        })
        # Keep only last 10
        self.recent_errors = self.recent_errors[-10:]

    @property
    def error_rate(self) -> float:
        if self.loop_iteration == 0:
            return 0.0
        return len(self.recent_errors) / self.loop_iteration

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_tools": self.active_tools,
            "loaded_skills": self.loaded_skills,
            "recent_errors": self.recent_errors[-3:],
            "error_rate": round(self.error_rate, 3),
            "current_task": self.current_task,
            "loop_iteration": self.loop_iteration,
            "memory_labels": self.memory_labels,
        }


class SubagentProjection:
    """Projected state of a subagent as seen by the controller."""

    def __init__(self, agent_id: str, task: str, persona: str = "worker"):
        self.agent_id = agent_id
        self.task = task
        self.persona = persona
        self.progress_pct: float = 0.0
        self.started_at: str = datetime.now().isoformat()
        self.estimated_remaining_s: float | None = None
        self.needs_from_controller: list[str] = []
        self.status: str = "running"  # running | blocked | completed | failed

    def update_progress(self, pct: float, remaining_s: float | None = None) -> None:
        self.progress_pct = min(100.0, pct)
        self.estimated_remaining_s = remaining_s

    def request_from_controller(self, description: str) -> None:
        """Seeker→Controller: signal that this subagent needs information."""
        self.needs_from_controller.append(description)
        self.status = "blocked"
        logger.info("Subagent {} requests from controller: {}", self.agent_id, description[:60])

    def fulfill_request(self, index: int = 0) -> str | None:
        """Controller fulfills a pending request."""
        if index < len(self.needs_from_controller):
            request = self.needs_from_controller.pop(index)
            if not self.needs_from_controller:
                self.status = "running"
            return request
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "task": self.task,
            "persona": self.persona,
            "progress_pct": self.progress_pct,
            "status": self.status,
            "estimated_remaining_s": self.estimated_remaining_s,
            "pending_requests": len(self.needs_from_controller),
        }


class AwarenessProjector:
    """Central awareness hub for the agent swarm.

    Maintains:
    - Self-awareness model for the main agent
    - Projected awareness of all active subagents
    - Cross-agent request pipeline (seeker→controller)
    """

    def __init__(self, workspace: Path):
        self._workspace = workspace
        self._snapshot_path = workspace / "processors" / "awareness_snapshot.json"
        self._snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        self.self_model = SelfAwareness()
        self._subagent_projections: dict[str, SubagentProjection] = {}

    # ── Subagent Management ────────────────────────────────────────

    def register_subagent(self, agent_id: str, task: str, persona: str = "worker") -> SubagentProjection:
        proj = SubagentProjection(agent_id, task, persona)
        self._subagent_projections[agent_id] = proj
        return proj

    def get_subagent(self, agent_id: str) -> SubagentProjection | None:
        return self._subagent_projections.get(agent_id)

    def complete_subagent(self, agent_id: str) -> None:
        proj = self._subagent_projections.get(agent_id)
        if proj:
            proj.status = "completed"
            proj.progress_pct = 100.0

    def remove_subagent(self, agent_id: str) -> None:
        self._subagent_projections.pop(agent_id, None)

    # ── Cross-Agent Requests ───────────────────────────────────────

    def get_pending_requests(self) -> list[dict[str, Any]]:
        """Get all blocked subagent requests the controller should address."""
        requests = []
        for agent_id, proj in self._subagent_projections.items():
            for i, req in enumerate(proj.needs_from_controller):
                requests.append({
                    "agent_id": agent_id,
                    "task": proj.task,
                    "request": req,
                    "request_index": i,
                })
        return requests

    # ── Snapshot ───────────────────────────────────────────────────

    def generate_snapshot(self) -> dict[str, Any]:
        """Generate the awareness snapshot for injection into context."""
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "self": self.self_model.to_dict(),
            "subagents": {
                aid: proj.to_dict()
                for aid, proj in self._subagent_projections.items()
            },
            "blocked_requests": self.get_pending_requests(),
            "swarm_size": len(self._subagent_projections),
            "swarm_health": self._compute_health(),
        }
        # Persist for debugging
        try:
            self._snapshot_path.write_text(
                json.dumps(snapshot, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass
        return snapshot

    def _compute_health(self) -> str:
        if not self._subagent_projections:
            return "idle"
        blocked = sum(1 for p in self._subagent_projections.values() if p.status == "blocked")
        failed = sum(1 for p in self._subagent_projections.values() if p.status == "failed")
        total = len(self._subagent_projections)
        if failed > total * 0.5:
            return "critical"
        if blocked > 0:
            return "degraded"
        return "healthy"

    def generate_context_string(self) -> str:
        """Generate a compact string for injection into the system prompt."""
        snap = self.generate_snapshot()
        lines = [f"## Swarm Awareness (health: {snap['swarm_health']})"]
        lines.append(f"Active tools: {len(snap['self']['active_tools'])}")
        lines.append(f"Skills loaded: {len(snap['self']['loaded_skills'])}")
        lines.append(f"Error rate: {snap['self']['error_rate']:.0%}")

        if snap["subagents"]:
            lines.append(f"\nSubagents ({snap['swarm_size']}):")
            for aid, sa in snap["subagents"].items():
                lines.append(f"  [{aid}] {sa['task'][:40]} — {sa['status']} ({sa['progress_pct']:.0f}%)")

        if snap["blocked_requests"]:
            lines.append(f"\n⚠ {len(snap['blocked_requests'])} pending requests from subagents")

        return "\n".join(lines)

    def render_status(self) -> str:
        return self.generate_context_string()
