"""Tool for querying the real-time execution bounds of the Swarm."""

import json
from typing import Any, TYPE_CHECKING
import textwrap

from nanobot.agent.tools.base import Tool

if TYPE_CHECKING:
    from nanobot.agent.subagent import SubagentManager
    from nanobot.agent.loop import AgentLoop


class SwarmStatusTool(Tool):
    """
    Tool to query the current execution state of the swarm.
    
    Provides visibility into active subagents and currently processing chat loops
    so the agent can intelligently manage its own parallelism and resources.
    """
    
    def __init__(self, manager: "SubagentManager", agent_loop: "AgentLoop"):
        self._manager = manager
        self._loop = agent_loop
    
    @property
    def name(self) -> str:
        return "swarm_status"
    
    @property
    def description(self) -> str:
        return (
            "Get the pragmatic status of the agent swarm's execution footprint. "
            "Use this to see how many background subagents are actively running, "
            "and what chat sessions are currently keeping the agent busy. "
            "If you need to evaluate whether to wait for a task to finish, or spawn "
            "a new capability, check the dashboard."
        )
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Currently only supports 'status'.",
                    "enum": ["status"]
                }
            },
            "required": ["action"],
        }
    
    async def execute(self, action: str = "status", **kwargs: Any) -> str:
        """Fetch and format the active status of the swarm."""
        if action != "status":
            return "Error: Unsupported action. Use 'status'."
            
        try:
            active_subagents = self._manager.get_active_subagents()
            active_sessions = list(self._loop._active_tasks.keys()) if hasattr(self._loop, "_active_tasks") else []
            pending_interrupts = list(self._loop._pending_interrupt.keys()) if hasattr(self._loop, "_pending_interrupt") else []
            
            output = ["= SWARM DASHBOARD: Parallel Operations ="]
            
            output.append("\n== Active Background Subagents ==")
            if not active_subagents:
                output.append("  (None running)")
            else:
                for task_id, desc in active_subagents.items():
                    output.append(f"  - [{task_id}]: {desc}")
            
            output.append("\n== Active Main Agent Sessions ==")
            if not active_sessions:
                output.append("  (None running)")
            else:
                for session_key in active_sessions:
                    output.append(f"  - Session [{session_key}] is currently processing an instruction loop.")
                    
            output.append("\n== Pending Interruptions ==")
            if not pending_interrupts:
                output.append("  (None)")
            else:
                for session_key in pending_interrupts:
                    output.append(f"  - Session [{session_key}] is paused waiting for user confirmation to cancel previous loop.")
                    
            return "\n".join(output)
            
        except Exception as e:
            return f"Error retrieving swarm status: {e}"
