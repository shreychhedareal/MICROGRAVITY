"""DAG-based Task Tree — dependency tracking, checkpointing, and process templates.

Provides a directed acyclic graph of tasks with:
- Prerequisite / dependency edges
- Status tracking (pending → in_progress → completed / failed)
- Progress checkpoints stored to the vector store
- Process template extraction from completed task sequences
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger


# ── Data Types ─────────────────────────────────────────────────────

class TaskNode:
    """A single node in the task DAG."""

    __slots__ = (
        "id", "title", "description", "status", "priority",
        "labels", "depends_on", "created_at", "updated_at",
        "checkpoints", "consequence",
    )

    def __init__(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        labels: list[str] | None = None,
        depends_on: list[str] | None = None,
        task_id: str | None = None,
    ):
        self.id: str = task_id or f"T-{uuid.uuid4().hex[:8]}"
        self.title = title
        self.description = description
        self.status: str = "pending"  # pending | in_progress | completed | failed
        self.priority = priority      # low | medium | high | critical
        self.labels: list[str] = labels or []
        self.depends_on: list[str] = depends_on or []
        self.created_at: str = datetime.now().isoformat()
        self.updated_at: str = self.created_at
        self.checkpoints: list[dict[str, str]] = []
        self.consequence: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "labels": self.labels,
            "depends_on": self.depends_on,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "checkpoints": self.checkpoints,
            "consequence": self.consequence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskNode:
        node = cls(
            title=data["title"],
            description=data.get("description", ""),
            priority=data.get("priority", "medium"),
            labels=data.get("labels"),
            depends_on=data.get("depends_on"),
            task_id=data.get("id"),
        )
        node.status = data.get("status", "pending")
        node.created_at = data.get("created_at", node.created_at)
        node.updated_at = data.get("updated_at", node.updated_at)
        node.checkpoints = data.get("checkpoints", [])
        node.consequence = data.get("consequence")
        return node


# ── Task Tree Manager ──────────────────────────────────────────────

class TaskTree:
    """LMDB-persisted DAG of tasks with dependency resolution.

    The tree is stored as a single JSON blob in the workspace
    at ``workspace/tasks/task_tree.json``.
    """

    def __init__(self, workspace: Path):
        self._path = workspace / "tasks" / "task_tree.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._nodes: dict[str, TaskNode] = {}
        self._load()

    # ── Persistence ────────────────────────────────────────────────

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for item in data.get("tasks", []):
                node = TaskNode.from_dict(item)
                self._nodes[node.id] = node
        except Exception as e:
            logger.warning("Failed to load task tree: %s", e)

    def _save(self) -> None:
        payload = {
            "version": 1,
            "updated_at": datetime.now().isoformat(),
            "tasks": [n.to_dict() for n in self._nodes.values()],
        }
        self._path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── CRUD ───────────────────────────────────────────────────────

    def add_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        labels: list[str] | None = None,
        depends_on: list[str] | None = None,
    ) -> TaskNode:
        """Create a new task node and persist."""
        node = TaskNode(
            title=title,
            description=description,
            priority=priority,
            labels=labels,
            depends_on=depends_on,
        )
        self._nodes[node.id] = node
        self._save()
        logger.info("Task created: {} — {}", node.id, title)
        return node

    def get_task(self, task_id: str) -> TaskNode | None:
        return self._nodes.get(task_id)

    def remove_task(self, task_id: str) -> bool:
        if task_id in self._nodes:
            del self._nodes[task_id]
            # Remove from dependency lists of other tasks
            for n in self._nodes.values():
                if task_id in n.depends_on:
                    n.depends_on.remove(task_id)
            self._save()
            return True
        return False

    # ── Status Transitions ─────────────────────────────────────────

    def start_task(self, task_id: str) -> str | None:
        """Move a task to in_progress if all dependencies are satisfied."""
        node = self._nodes.get(task_id)
        if not node:
            return "Task not found."
        blocked = self.get_blocked_by(task_id)
        if blocked:
            titles = [self._nodes[b].title for b in blocked if b in self._nodes]
            return f"Blocked by: {', '.join(titles)}"
        node.status = "in_progress"
        node.updated_at = datetime.now().isoformat()
        self._save()
        return None

    def complete_task(self, task_id: str, consequence: str | None = None) -> bool:
        """Mark a task as completed with an optional consequence summary."""
        node = self._nodes.get(task_id)
        if not node:
            return False
        node.status = "completed"
        node.consequence = consequence
        node.updated_at = datetime.now().isoformat()
        self._save()
        return True

    def fail_task(self, task_id: str, reason: str = "") -> bool:
        node = self._nodes.get(task_id)
        if not node:
            return False
        node.status = "failed"
        node.updated_at = datetime.now().isoformat()
        node.checkpoints.append({
            "type": "failure",
            "timestamp": datetime.now().isoformat(),
            "note": reason,
        })
        self._save()
        return True

    # ── Checkpointing ──────────────────────────────────────────────

    def checkpoint(self, task_id: str, note: str) -> bool:
        """Add a progress checkpoint to a task."""
        node = self._nodes.get(task_id)
        if not node:
            return False
        node.checkpoints.append({
            "type": "progress",
            "timestamp": datetime.now().isoformat(),
            "note": note,
        })
        node.updated_at = datetime.now().isoformat()
        self._save()
        return True

    # ── DAG Queries ────────────────────────────────────────────────

    def get_blocked_by(self, task_id: str) -> list[str]:
        """Return IDs of incomplete dependencies blocking this task."""
        node = self._nodes.get(task_id)
        if not node:
            return []
        return [
            dep_id for dep_id in node.depends_on
            if dep_id in self._nodes
            and self._nodes[dep_id].status not in ("completed",)
        ]

    def get_ready_tasks(self) -> list[TaskNode]:
        """Return all pending tasks whose dependencies are fully satisfied."""
        ready = []
        for node in self._nodes.values():
            if node.status != "pending":
                continue
            blocked = self.get_blocked_by(node.id)
            if not blocked:
                ready.append(node)
        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        ready.sort(key=lambda n: priority_order.get(n.priority, 2))
        return ready

    def get_active_tasks(self) -> list[TaskNode]:
        """Return all in-progress tasks."""
        return [n for n in self._nodes.values() if n.status == "in_progress"]

    def get_all_tasks(self) -> list[TaskNode]:
        return list(self._nodes.values())

    # ── Process Templates ──────────────────────────────────────────

    def extract_template(self, task_ids: list[str]) -> dict[str, Any]:
        """Extract a reusable process template from a set of completed tasks.

        This captures the task sequence, dependencies, and labels to
        create a template that can be instantiated for similar future work.
        """
        steps = []
        for tid in task_ids:
            node = self._nodes.get(tid)
            if not node:
                continue
            steps.append({
                "title_template": node.title,
                "description_template": node.description,
                "labels": node.labels,
                "depends_on_step": [
                    task_ids.index(d) for d in node.depends_on
                    if d in task_ids
                ],
            })
        return {
            "version": 1,
            "created_at": datetime.now().isoformat(),
            "steps": steps,
        }

    def instantiate_template(
        self,
        template: dict[str, Any],
        title_prefix: str = "",
    ) -> list[TaskNode]:
        """Create tasks from a process template."""
        step_id_map: dict[int, str] = {}
        new_nodes: list[TaskNode] = []

        for idx, step in enumerate(template.get("steps", [])):
            depends_on = [
                step_id_map[dep_idx]
                for dep_idx in step.get("depends_on_step", [])
                if dep_idx in step_id_map
            ]
            title = f"{title_prefix}{step['title_template']}" if title_prefix else step["title_template"]
            node = self.add_task(
                title=title,
                description=step.get("description_template", ""),
                labels=step.get("labels", []),
                depends_on=depends_on,
            )
            step_id_map[idx] = node.id
            new_nodes.append(node)

        return new_nodes

    # ── Rendering ──────────────────────────────────────────────────

    def render_tree(self) -> str:
        """Render the task tree as a human-readable string."""
        if not self._nodes:
            return "Task Tree: Empty."

        lines = ["=== TASK TREE ==="]
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_nodes = sorted(
            self._nodes.values(),
            key=lambda n: (priority_order.get(n.priority, 2), n.created_at),
        )

        status_icons = {
            "pending": "○",
            "in_progress": "◐",
            "completed": "●",
            "failed": "✗",
        }

        for node in sorted_nodes:
            icon = status_icons.get(node.status, "?")
            deps_str = ""
            if node.depends_on:
                dep_titles = []
                for d in node.depends_on:
                    dep_node = self._nodes.get(d)
                    dep_titles.append(dep_node.title if dep_node else d)
                deps_str = f" [depends: {', '.join(dep_titles)}]"
            labels_str = f" {node.labels}" if node.labels else ""
            lines.append(
                f"  {icon} [{node.id}] {node.title} "
                f"({node.priority}){deps_str}{labels_str}"
            )
            if node.checkpoints:
                last_cp = node.checkpoints[-1]
                lines.append(f"      └─ {last_cp['type']}: {last_cp['note'][:60]}")

        return "\n".join(lines)
