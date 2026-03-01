"""Spawn tool for creating background subagents."""

from typing import Any, TYPE_CHECKING

from nanobot.agent.tools.base import Tool

if TYPE_CHECKING:
    from nanobot.agent.subagent import SubagentManager


class SpawnTool(Tool):
    """
    Tool to spawn a subagent for background task execution.
    
    The subagent runs asynchronously and announces its result back
    to the main agent when complete.
    """
    
    def __init__(self, manager: "SubagentManager"):
        self._manager = manager
        self._origin_channel = "cli"
        self._origin_chat_id = "direct"
    
    def set_context(self, channel: str, chat_id: str) -> None:
        """Set the origin context for subagent announcements."""
        self._origin_channel = channel
        self._origin_chat_id = chat_id
    
    @property
    def name(self) -> str:
        return "spawn"
    
    @property
    def description(self) -> str:
        return (
            "Spawner tool to manage background subagents. "
            "Action 'spawn': Spawn a subagent to handle a complex/time-consuming task independently. "
            "Action 'cancel': Cancel a currently running subagent by its task_id if the user requests it."
        )
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The action to perform: 'spawn' or 'cancel'. Defaults to 'spawn'.",
                    "default": "spawn",
                },
                "task": {
                    "type": "string",
                    "description": "The task for the subagent to complete (required for 'spawn')",
                },
                "label": {
                    "type": "string",
                    "description": "Optional short label for the task (for display)",
                },
                "task_id": {
                    "type": "string",
                    "description": "The ID of the subagent to cancel (required for 'cancel')",
                }
            },
        }
    
    async def execute(self, action: str = "spawn", task: str | None = None, label: str | None = None, task_id: str | None = None, **kwargs: Any) -> str:
        """Spawn or cancel a subagent."""
        if action == "cancel":
            if not task_id:
                return "Error: 'task_id' is required to cancel a subagent."
            return await self._manager.cancel(task_id)
            
        if not task:
            return "Error: 'task' is required to spawn a subagent."
            
        return await self._manager.spawn(
            task=task,
            label=label,
            origin_channel=self._origin_channel,
            origin_chat_id=self._origin_chat_id,
        )
