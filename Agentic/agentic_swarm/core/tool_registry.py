import json
import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class RegisteredTool(BaseModel):
    name: str = Field(description="The formal identifier of the tool.")
    purpose: str = Field(description="What specific problem does this solve?")
    how_to: str = Field(description="Exact mechanical syntax or code snippet required to use this tool.")
    when_to: str = Field(description="Heuristics on when this tool is optimal over others.")
    dependencies: List[str] = Field(default_factory=list, description="Required software or pip packages.")

class ToolRegistry:
    """
    The global catalog of available software, APIs, and custom scripts. 
    Seekers read this to know 'how' to execute, Operator reads to know 'what' is available.
    """
    def __init__(self):
        self._tools: Dict[str, RegisteredTool] = {}
        self._seed_default_tools()
        
    def _seed_default_tools(self):
        """Seed the basic built-in OS utilities for MVP."""
        self.register(RegisteredTool(
            name="curl",
            purpose="Making generic HTTP calls or interacting with REST APIs.",
            how_to="curl -X POST -H 'Content-Type: application/json' -d '{\"key\":\"val\"}' [URL]",
            when_to="When you need to ping an external service or MCP server without writing a python script.",
            dependencies=["curl"]
        ))
        
        self.register(RegisteredTool(
            name="pytest",
            purpose="Running automated test suites on Python code.",
            how_to="pytest [directory] -v",
            when_to="After the QASeeker has written unit tests and needs to verify them.",
            dependencies=["pytest"]
        ))

    def register(self, tool: RegisteredTool):
        """Adds a new tool (like a custom script created by ActionSeeker) to the catalog."""
        self._tools[tool.name] = tool
        logger.info(f"🔧 Tool Registered: {tool.name}")

    def get_tool(self, name: str) -> RegisteredTool:
        return self._tools.get(name)
        
    def get_all_summaries(self) -> str:
        """Returns a string formatted context block for LLM prompt injection."""
        summaries = []
        for name, tool in self._tools.items():
            summaries.append(f"[{name}] - Purpose: {tool.purpose} | When to use: {tool.when_to}")
        return "\n".join(summaries)
        
    def get_how_to(self, name: str) -> str:
        """Returns the strict execution mechanical syntax for a tool."""
        tool = self._tools.get(name)
        return tool.how_to if tool else "Tool not found."
