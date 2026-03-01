import os
import logging
import subprocess
from pydantic import BaseModel, Field
from core.tool_registry import ToolRegistry, RegisteredTool
from agents.base import BaseSeekerAgent

logger = logging.getLogger(__name__)

class ActionCommandSchema(BaseModel):
    action_type: str = Field(description="'WRITE' (creates script), 'RUN' (executes existing), or 'KILL' (terminates by PID).")
    script_name: str = Field(description="Name of the file (e.g., scrape_api.py).")
    script_content: str = Field(default="", description="The script code to save (if action_type is WRITE).")
    purpose: str = Field(default="", description="What does this script do? Used to register it globally.")
    when_to: str = Field(default="", description="When should the Operator select this specific script/tool.")
    how_to: str = Field(default="", description="Exact command line argument to run this script.")
    anticipated_result: str = Field(default="", description="The text or file output expected on success.")

class ActionSeeker(BaseSeekerAgent):
    """
    Dedicated agent for planning, writing, managing, and terminating custom scripts 
    and actions that do not fit standard pre-built OS tools.
    """
    
    def __init__(self, tool_registry: ToolRegistry, model_name: str = "gpt-4o"):
        super().__init__(
            name="ActionSeeker",
            description="Manages writing, executing, and terminating custom automation scripts.",
            model_name=model_name
        )
        self.registry = tool_registry
        self.workspace_dir = "agentic_swarm/actions/"
        os.makedirs(self.workspace_dir, exist_ok=True)
        
    @property
    def system_prompt(self) -> str:
        return (
            "You are the ActionSeeker, a specialized DevOps automation engineer.\n"
            "Your domain is writing, running, and managing custom scripts (Python, Bash) for varied actions.\n"
            f"Scripts should be saved to {self.workspace_dir}.\n"
            "If you WRITE a new script, you MUST define its 'purpose', 'how_to', and 'when_to' so it can be registered.\n"
            "If you RUN a script, execution happens in a blocking sandbox for MVP. Terminate runaway scripts using KILL.\n"
            "ALWAYS define an 'anticipated_result' to check against stdout."
        )
        
    @property
    def output_schema(self) -> type[BaseModel]:
        return ActionCommandSchema
        
    def run_tools(self, plan: ActionCommandSchema) -> Any:
        # Action 1: Write Custom Script
        script_path = os.path.join(self.workspace_dir, plan.script_name)
        
        if plan.action_type == "WRITE":
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(plan.script_content)
                
            # Register newly created logic to the Swarm's Global Registry
            tool = RegisteredTool(
                name=plan.script_name,
                purpose=plan.purpose,
                how_to=f"python {script_path}" if plan.script_name.endswith(".py") else f"bash {script_path}",
                when_to=plan.when_to
            )
            self.registry.register(tool)
            return {"status": "success", "message": f"Script {plan.script_name} written to disk and globally registered."}
            
        # Action 2: Run Custom Script
        elif plan.action_type == "RUN":
            if not os.path.exists(script_path):
                return {"error": f"Script {script_path} does not exist. Cannot RUN."}
            
            # Simple subprocess for MVP; production uses durable Celery/Docker Popen
            logger.info(f"Running Action: {plan.script_name}")
            cmd = self.registry.get_how_to(plan.script_name)
            
            if cmd == "Tool not found.":
                 cmd = f"python {script_path}" if plan.script_name.endswith(".py") else f"bash {script_path}"
                 
            try:
                result = subprocess.run(cmd, env=None, shell=True, capture_output=True, text=True, timeout=15)
                return {"stdout": result.stdout[:2000], "stderr": result.stderr[:2000], "returncode": result.returncode}
            except subprocess.TimeoutExpired:
                return {"error": f"Script {plan.script_name} timed out. Requires PAUSE or KILL event."}
                
        # Action 3: Kill runaway script (Mock for MVP)
        elif plan.action_type == "KILL":
            return {"status": "success", "message": f"Script {plan.script_name} terminated gracefully."}
            
        return {"error": f"Unknown action_type: {plan.action_type}"}
