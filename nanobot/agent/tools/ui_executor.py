"""Tool for executing robust GUI workflows using the AntiGravity UI Agent Engine."""

import os
import sys
import logging
from typing import TYPE_CHECKING, Any
from nanobot.agent.tools.base import Tool

if TYPE_CHECKING:
    from nanobot.providers.base import LLMProvider
    from nanobot.agent.loop import AgentLoop

logger = logging.getLogger("nanobot.ui_executor")

class UIAgentExecutorTool(Tool):
    """
    Exposes the robust AntiGravity UI Agent (with CV Tracking, Hybrid Validation, 
    and Semantic Recovery LOOPS) to the Swarm.
    """
    
    def __init__(self, workspace: str):
        self.workspace = workspace
        
        # We need to dynamically import the UIAgent from the embedded ui_agent_engine directory
        # The workspace is c:\\Users\\HP\\nanobot
        ui_agent_path = os.path.join(self.workspace, "ui_agent_engine")
        if ui_agent_path not in sys.path:
            sys.path.append(ui_agent_path)
            
        try:
            # Add the immediate src directly so internal relative imports work
            src_path = os.path.join(ui_agent_path, "src")
            if src_path not in sys.path:
                 sys.path.append(src_path)
        except Exception as e:
            logger.error(f"Failed to append UI Agent src path: {e}")
            
    @property
    def name(self) -> str:
        return "ui_executor"
        
    @property
    def description(self) -> str:
        return (
            "Powerful Execution Engine for ALL complex desktop UI workflows (e.g. 'Log into Website', 'Open Settings'). "
            "Use this tool when you need to physically automate the user's computer via Mouse/Keyboard interactions "
            "instead of attempting manual coordinate math or scripting. "
            "It supports semantic recovery, computer vision tracking, and complex drag-and-drop operations."
        )
        
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "Required. A high-level description of what the UI orchestrator should achieve physically."
                }
            },
            "required": ["goal"],
        }
        
    async def execute(self, goal: str, **kwargs: Any) -> str:
        """Execute the Goal via the UIAgent Engine."""
        logger.info(f"Delegating Goal to AntiGravity UI Agent: '{goal}'")
        
        try:
            from agent_core.ui_agent import UIAgent
            
            # 1. Instantiate the heavy UI orchestrator
            # Note: This loads the CV Static Map JSON cache into RAM automatically.
            agent = UIAgent()
            
            # 2. Assign the overarching task
            agent.receive_task(goal)
            
            # 3. Block and execute the Observe-Think-Act-Recover loop exclusively.
            logger.info("Transferring execution control to UIAgent Loop...")
            agent.run()
            
            # 4. Agent terminated loop either functionally complete or totally failed
            logger.info("UIAgent execution returned control.")
            
            # Extract final status
            tasks_remaining = len(agent.goal_manager.subtasks)
            completed_tasks = len(agent.goal_manager.completed_tasks)
            
            if tasks_remaining == 0 and completed_tasks > 0:
                 return f"UI Execution Engine reports SUCCESS. Goal '{goal}' achieved. Completed {completed_tasks} physical tasks via CV Engine."
            else:
                 return f"UI Execution Engine aborted with {tasks_remaining} unrecoverable failures. Check execution trace for screen state details."
                 
        except Exception as e:
            return f"Error booting or communicating with the external AntiGravity UI Agent: {str(e)}"
