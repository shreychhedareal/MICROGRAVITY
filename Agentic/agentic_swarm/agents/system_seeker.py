from pydantic import BaseModel, Field
import subprocess
import logging
from typing import Dict, Any

from agents.base import BaseSeekerAgent

logger = logging.getLogger(__name__)

class SystemCommandSchema(BaseModel):
    command: str = Field(description="The exact terminal command to run.")
    reasoning: str = Field(description="Why this command is being executed.")
    is_safe: bool = Field(description="True if this command does not delete or dangerously mutate the system.")
    anticipated_result: str = Field(default="", description="The specific words or patterns you expect to see in the terminal output if successful.")

class SystemSeeker(BaseSeekerAgent):
    """
    A specialized agent that executes safe terminal commands or interacts with the local file system.
    """
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        super().__init__(
            name="SystemSeeker",
            description="Executes terminal commands, file manipulations, and reads system state.",
            model_name=model_name
        )

    @property
    def system_prompt(self) -> str:
        return (
            "You are a System Seeker agent. Your job is to strictly analyze an objective and generate a terminal command.\n"
            "You must use powershell syntax (e.g. ls, cat, etc.) as the target OS is Windows.\n"
            "CRITICAL:\n"
            "1. Do not use destructive commands (rm -rf /, format, etc.).\n"
            "2. Always output valid JSON matching the exact schema."
        )

    @property
    def output_schema(self) -> type[BaseModel]:
        return SystemCommandSchema

    def run_tools(self, parsed_objective: BaseModel) -> Any:
        """
        Executes the derived shell command safely.
        """
        command_data: SystemCommandSchema = parsed_objective
        
        if not command_data.is_safe:
            raise ValueError(f"Agent determined command '{command_data.command}' as unsafe to execute automatically.")
            
        logger.info(f"Executing System Command: {command_data.command}")
        
        try:
            # We use powershell on windows. In a real environment, run within Docker or secure sandbox.
            # timeout added to prevent infinite hanging
            result = subprocess.run(
                ["powershell", "-Command", command_data.command],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout if result.returncode == 0 else result.stderr
            return {
                "return_code": result.returncode,
                "output": output[:1000] # Truncate output to avoid state explosion
            }
            
        except subprocess.TimeoutExpired:
            raise Exception("Command execution timed out.")
        except Exception as e:
            raise Exception(f"Failed to execute command: {str(e)}")
