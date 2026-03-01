"""Unified Trigger Scheduler — time, event, and consequence-driven dispatch.

Provides a single dispatcher that coordinates:
- **Time-based triggers**: Cron-style recurring schedules
- **Event-driven triggers**: Fire when specific label clusters receive new data
- **Consequence-driven triggers**: Fire when a task completes with a matching consequence

All triggers produce ``ScheduledAction`` objects that are fed into a
priority queue for the Agent Loop or SubagentManager to consume.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable

from loguru import logger


# ── Trigger Types ──────────────────────────────────────────────────

class Trigger:
    """Base class for all trigger types."""

    __slots__ = ("id", "name", "enabled", "created_at")

    def __init__(self, name: str, trigger_id: str | None = None):
        self.id = trigger_id or f"TRG-{uuid.uuid4().hex[:8]}"
        self.name = name
        self.enabled = True
        self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.__class__.__name__,
            "name": self.name,
            "enabled": self.enabled,
            "created_at": self.created_at,
        }


class EventTrigger(Trigger):
    """Fires when a new entry is stored with matching labels."""

    def __init__(
        self,
        name: str,
        watch_labels: list[str],
        action_description: str,
        trigger_id: str | None = None,
    ):
        super().__init__(name, trigger_id)
        self.watch_labels = watch_labels
        self.action_description = action_description

    def matches(self, labels: list[str]) -> bool:
        """Check if the incoming labels intersect with our watch set."""
        return bool(set(self.watch_labels) & set(labels))

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["watch_labels"] = self.watch_labels
        d["action_description"] = self.action_description
        return d


class ConsequenceTrigger(Trigger):
    """Fires when a task completes whose consequence matches keywords."""

    def __init__(
        self,
        name: str,
        watch_keywords: list[str],
        action_description: str,
        trigger_id: str | None = None,
    ):
        super().__init__(name, trigger_id)
        self.watch_keywords = [kw.lower() for kw in watch_keywords]
        self.action_description = action_description

    def matches(self, consequence_text: str) -> bool:
        lower = consequence_text.lower()
        return any(kw in lower for kw in self.watch_keywords)

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["watch_keywords"] = self.watch_keywords
        d["action_description"] = self.action_description
        return d


# ── Scheduled Actions ──────────────────────────────────────────────

class ScheduledAction:
    """An action produced by a trigger, queued for execution."""

    def __init__(
        self,
        trigger: Trigger,
        description: str,
        priority: str = "medium",
        context: dict[str, Any] | None = None,
    ):
        self.id = f"ACT-{uuid.uuid4().hex[:8]}"
        self.trigger_id = trigger.id
        self.trigger_name = trigger.name
        self.description = description
        self.priority = priority
        self.context = context or {}
        self.created_at = datetime.now().isoformat()
        self.status = "queued"  # queued | dispatched | completed | failed

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "trigger_id": self.trigger_id,
            "trigger_name": self.trigger_name,
            "description": self.description,
            "priority": self.priority,
            "context": self.context,
            "created_at": self.created_at,
            "status": self.status,
        }


# ── Scheduler ──────────────────────────────────────────────────────

class Scheduler:
    """Unified trigger dispatcher for the swarm.

    Manages event and consequence triggers. Time-based triggers are
    handled by the existing ``CronService``; this scheduler focuses on
    reactive triggers that fire in response to data changes.
    """

    def __init__(self, workspace: Path):
        self._path = workspace / "scheduler" / "triggers.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._event_triggers: dict[str, EventTrigger] = {}
        self._consequence_triggers: dict[str, ConsequenceTrigger] = {}
        self._action_queue: list[ScheduledAction] = []
        self._action_log: list[dict[str, Any]] = []
        self._callbacks: list[Callable[[ScheduledAction], Awaitable[None]]] = []
        self._load()

    # ── Persistence ────────────────────────────────────────────────

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for t in data.get("event_triggers", []):
                trigger = EventTrigger(
                    name=t["name"],
                    watch_labels=t["watch_labels"],
                    action_description=t["action_description"],
                    trigger_id=t.get("id"),
                )
                trigger.enabled = t.get("enabled", True)
                self._event_triggers[trigger.id] = trigger

            for t in data.get("consequence_triggers", []):
                trigger = ConsequenceTrigger(
                    name=t["name"],
                    watch_keywords=t["watch_keywords"],
                    action_description=t["action_description"],
                    trigger_id=t.get("id"),
                )
                trigger.enabled = t.get("enabled", True)
                self._consequence_triggers[trigger.id] = trigger
        except Exception as e:
            logger.warning("Failed to load scheduler triggers: %s", e)

    def _save(self) -> None:
        payload = {
            "version": 1,
            "updated_at": datetime.now().isoformat(),
            "event_triggers": [t.to_dict() for t in self._event_triggers.values()],
            "consequence_triggers": [t.to_dict() for t in self._consequence_triggers.values()],
        }
        self._path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── Registration ───────────────────────────────────────────────

    def register_event_trigger(
        self,
        name: str,
        watch_labels: list[str],
        action_description: str,
    ) -> EventTrigger:
        """Register a new event trigger that fires when matching labels are stored."""
        trigger = EventTrigger(name, watch_labels, action_description)
        self._event_triggers[trigger.id] = trigger
        self._save()
        logger.info("Registered event trigger: {} watching {}", name, watch_labels)
        return trigger

    def register_consequence_trigger(
        self,
        name: str,
        watch_keywords: list[str],
        action_description: str,
    ) -> ConsequenceTrigger:
        """Register a trigger that fires on task completion with matching consequences."""
        trigger = ConsequenceTrigger(name, watch_keywords, action_description)
        self._consequence_triggers[trigger.id] = trigger
        self._save()
        logger.info("Registered consequence trigger: {} watching {}", name, watch_keywords)
        return trigger

    def remove_trigger(self, trigger_id: str) -> bool:
        removed = False
        if trigger_id in self._event_triggers:
            del self._event_triggers[trigger_id]
            removed = True
        if trigger_id in self._consequence_triggers:
            del self._consequence_triggers[trigger_id]
            removed = True
        if removed:
            self._save()
        return removed

    # ── Listener Registration ──────────────────────────────────────

    def on_action(self, callback: Callable[[ScheduledAction], Awaitable[None]]) -> None:
        """Register an async callback to receive scheduled actions."""
        self._callbacks.append(callback)

    # ── Event Processing ───────────────────────────────────────────

    async def on_data_stored(self, labels: list[str], text: str) -> list[ScheduledAction]:
        """Called when new data is stored in the vector store.

        Checks all event triggers and fires matching ones.
        """
        fired: list[ScheduledAction] = []
        for trigger in self._event_triggers.values():
            if not trigger.enabled:
                continue
            if trigger.matches(labels):
                action = ScheduledAction(
                    trigger=trigger,
                    description=trigger.action_description,
                    context={"matched_labels": labels, "text_preview": text[:200]},
                )
                fired.append(action)
                self._action_queue.append(action)
                self._action_log.append(action.to_dict())
                logger.info("Event trigger fired: {} → {}", trigger.name, action.id)
                for cb in self._callbacks:
                    try:
                        await cb(action)
                    except Exception as e:
                        logger.warning("Callback error for action {}: {}", action.id, e)
        return fired

    async def on_task_completed(self, consequence: str) -> list[ScheduledAction]:
        """Called when a task completes with a consequence.

        Checks all consequence triggers and fires matching ones.
        """
        fired: list[ScheduledAction] = []
        for trigger in self._consequence_triggers.values():
            if not trigger.enabled:
                continue
            if trigger.matches(consequence):
                action = ScheduledAction(
                    trigger=trigger,
                    description=trigger.action_description,
                    priority="high",
                    context={"consequence": consequence[:200]},
                )
                fired.append(action)
                self._action_queue.append(action)
                self._action_log.append(action.to_dict())
                logger.info("Consequence trigger fired: {} → {}", trigger.name, action.id)
                for cb in self._callbacks:
                    try:
                        await cb(action)
                    except Exception as e:
                        logger.warning("Callback error for action {}: {}", action.id, e)
        return fired

    # ── Queue Management ───────────────────────────────────────────

    def get_pending_actions(self) -> list[ScheduledAction]:
        """Return all queued actions sorted by priority."""
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return sorted(
            [a for a in self._action_queue if a.status == "queued"],
            key=lambda a: priority_order.get(a.priority, 2),
        )

    def mark_dispatched(self, action_id: str) -> None:
        for action in self._action_queue:
            if action.id == action_id:
                action.status = "dispatched"
                return

    def mark_completed(self, action_id: str) -> None:
        for action in self._action_queue:
            if action.id == action_id:
                action.status = "completed"
                return

    # ── Introspection ──────────────────────────────────────────────

    def list_triggers(self) -> list[dict[str, Any]]:
        """List all registered triggers."""
        triggers = []
        for t in self._event_triggers.values():
            triggers.append(t.to_dict())
        for t in self._consequence_triggers.values():
            triggers.append(t.to_dict())
        return triggers

    def get_action_log(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return the most recent triggered actions."""
        return self._action_log[-limit:]

    def render_status(self) -> str:
        """Render a human-readable scheduler status."""
        lines = ["=== SCHEDULER STATUS ==="]
        lines.append(f"Event triggers: {len(self._event_triggers)}")
        lines.append(f"Consequence triggers: {len(self._consequence_triggers)}")

        pending = self.get_pending_actions()
        lines.append(f"Pending actions: {len(pending)}")

        if pending:
            lines.append("\n--- Pending Actions ---")
            for a in pending[:5]:
                lines.append(f"  [{a.id}] {a.description[:60]} (priority: {a.priority})")

        return "\n".join(lines)
