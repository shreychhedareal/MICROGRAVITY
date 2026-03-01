"""DAG-backed task management tools for the swarm.

Provides LLM-callable tools for creating tasks with dependencies,
checkpointing progress, completing tasks with consequences, and
viewing the task tree.
"""

from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool
from nanobot.agent.task_tree import TaskTree
from nanobot.agent.memory import MemoryStore


class TaskTrackerTool(Tool):
    """Tool to manage the swarm's DAG-based task tree.

    Supports creating tasks with dependencies, starting/completing them,
    adding checkpoints, and rendering the full tree.
    """

    def __init__(self, workspace_path: str | Path):
        self._workspace = Path(workspace_path).expanduser().resolve()
        self._tree = TaskTree(self._workspace)
        self._memory = MemoryStore(self._workspace)

    @property
    def name(self) -> str:
        return "task_tracker"

    @property
    def description(self) -> str:
        return (
            "Manage the Swarm's DAG-based task tree with dependencies, priorities, and checkpoints. "
            "Actions: 'add' (create task), 'start' (begin work), 'complete' (finish with consequence), "
            "'fail' (mark failed), 'checkpoint' (save progress), 'view' (render tree), "
            "'ready' (list unblocked tasks)."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The operation to perform",
                    "enum": ["add", "start", "complete", "fail", "checkpoint", "view", "ready"]
                },
                "title": {
                    "type": "string",
                    "description": "Task title (required for 'add')"
                },
                "description": {
                    "type": "string",
                    "description": "Task description (optional for 'add')"
                },
                "task_id": {
                    "type": "string",
                    "description": "Task ID (required for start/complete/fail/checkpoint)"
                },
                "priority": {
                    "type": "string",
                    "description": "Priority level",
                    "enum": ["low", "medium", "high", "critical"]
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Categorical labels for clustering"
                },
                "depends_on": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of task IDs this task depends on"
                },
                "consequence": {
                    "type": "string",
                    "description": "Summary of the outcome (for 'complete')"
                },
                "note": {
                    "type": "string",
                    "description": "Progress note (for 'checkpoint') or failure reason (for 'fail')"
                },
            },
            "required": ["action"],
        }

    async def execute(
        self,
        action: str,
        title: str | None = None,
        description: str | None = None,
        task_id: str | None = None,
        priority: str = "medium",
        labels: list[str] | None = None,
        depends_on: list[str] | None = None,
        consequence: str | None = None,
        note: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            if action == "add":
                if not title:
                    return "Error: 'title' is required for action 'add'."
                node = self._tree.add_task(
                    title=title,
                    description=description or "",
                    priority=priority,
                    labels=labels,
                    depends_on=depends_on,
                )
                return f"Created task [{node.id}]: {node.title} (priority: {node.priority})"

            elif action == "start":
                if not task_id:
                    return "Error: 'task_id' is required for action 'start'."
                err = self._tree.start_task(task_id)
                if err:
                    return f"Cannot start task: {err}"
                return f"Task {task_id} is now in progress."

            elif action == "complete":
                if not task_id:
                    return "Error: 'task_id' is required for action 'complete'."
                ok = self._tree.complete_task(task_id, consequence=consequence)
                if not ok:
                    return f"Task {task_id} not found."
                # Also store consequence in vector memory if provided
                if consequence:
                    domain_labels = labels or []
                    task = self._tree.get_task(task_id)
                    if task and task.labels:
                        domain_labels = list(set(domain_labels + task.labels))
                    self._memory.store_consequence(consequence, domain_labels=domain_labels)
                return f"Task {task_id} completed." + (f" Consequence stored." if consequence else "")

            elif action == "fail":
                if not task_id:
                    return "Error: 'task_id' is required for action 'fail'."
                ok = self._tree.fail_task(task_id, reason=note or "")
                if not ok:
                    return f"Task {task_id} not found."
                return f"Task {task_id} marked as failed."

            elif action == "checkpoint":
                if not task_id or not note:
                    return "Error: 'task_id' and 'note' are required for action 'checkpoint'."
                ok = self._tree.checkpoint(task_id, note)
                if not ok:
                    return f"Task {task_id} not found."
                return f"Checkpoint saved for task {task_id}."

            elif action == "view":
                return self._tree.render_tree()

            elif action == "ready":
                ready = self._tree.get_ready_tasks()
                if not ready:
                    return "No tasks are ready to start (all blocked or none pending)."
                lines = ["Ready tasks (unblocked):"]
                for node in ready:
                    lines.append(f"  [{node.id}] {node.title} (priority: {node.priority})")
                return "\n".join(lines)

            else:
                return f"Unknown action: '{action}'."

        except Exception as e:
            return f"Task tracker error: {e}"
