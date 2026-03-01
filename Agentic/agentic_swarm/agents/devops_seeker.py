from pydantic import BaseModel, Field
import logging
from typing import Any

from agents.base import BaseSeekerAgent

logger = logging.getLogger(__name__)

class DevOpsSchema(BaseModel):
    action: str = Field(description="Action to perform: 'monitor_resources', 'start_cron', or 'kill_process'.")
    target_process: str = Field(default="", description="Name or ID of process to monitor or kill (optional).")
    cron_interval: str = Field(default="", description="Cron syntax string if action is start_cron.")

class DevOpsSeeker(BaseSeekerAgent):
    """
    DevOps Seeker: Manages system resources, monitors processes, and schedules recurring tasks.
    """
    def __init__(self, model_name: str = "gpt-4o-mini"):
        super().__init__(
            name="DevOpsSeeker",
            description="Tracks resources, sets up cron jobs, and manages running background processes.",
            model_name=model_name
        )

    @property
    def system_prompt(self) -> str:
        return (
            "You are the DevOps Seeker agent. Your domain is resource tracking, cron job scheduling, "
            "and active process management.\n"
            "CRITICAL:\n"
            "1. Output valid JSON matching the exact schema.\n"
            "2. Identify the correct action from the user's objective."
        )

    @property
    def output_schema(self) -> type[BaseModel]:
        return DevOpsSchema

    def run_tools(self, parsed_objective: BaseModel) -> Any:
        devops_data: DevOpsSchema = parsed_objective
        logger.info(f"Executing DevOps Action: {devops_data.action} on '{devops_data.target_process}'")
        
        # Mock logic
        message = ""
        if devops_data.action == "monitor_resources":
            message = "CPU Usage: 12%, Memory: 4.2GB used."
        elif devops_data.action == "start_cron":
            message = f"Scheduled task with interval '{devops_data.cron_interval}'."
        elif devops_data.action == "kill_process":
            message = f"Terminated process '{devops_data.target_process}'."
        else:
            message = "Unknown action."
            
        return {
            "action": devops_data.action,
            "result_summary": message
        }
