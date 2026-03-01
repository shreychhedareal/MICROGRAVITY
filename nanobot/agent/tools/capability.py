from pathlib import Path
from typing import Any, Dict
from nanobot.agent.tools.base import Tool
from loguru import logger

class AnalyzeCapabilityExpansionTool(Tool):
    """
    Analyzes whether the current Swarm can handle a complex request
    or if it needs to build a new capability/tool.
    """
    name = "analyze_capability"
    description = (
        "Run this tool if a user request seems out of reach for current tools. "
        "It analyzes SYSTEM_CATALOG.md and EVOLUTION_LEDGER.json to determine feasibility."
    )

    def __init__(self, workspace: Path):
        self.workspace = workspace

    async def execute(self, user_request: str) -> str:
        logger.info(f"Analyzing capability expansion for request: {user_request[:50]}...")
        
        catalog_path = self.workspace / "SYSTEM_CATALOG.md"
        ledger_path = self.workspace / "memory" / "EVOLUTION_LEDGER.json"
        
        catalog = "(Not found)"
        if catalog_path.exists():
            catalog = catalog_path.read_text(encoding="utf-8")
            
        ledger = "(Not found)"
        if ledger_path.exists():
            ledger = ledger_path.read_text(encoding="utf-8")

        # This tool returns the raw context to the LLM so it can decide what to do
        # instead of trying to parse its own proprietary JSON format.
        report = (
            f"### SYSTEM CAPABILITY ANALYSIS\n\n"
            f"**Current Catalog:**\n{catalog[:1000]}...\n\n"
            f"**Evolution Ledger:**\n{ledger[:500]}...\n\n"
            f"**Conclusion:** The swarm has sufficient base logic. "
            f"If the required tool is missing, use 'execute_shell' or 'write_file' to build it."
        )
        return report

    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "user_request": {
                        "type": "string",
                        "description": "The specific feature or expansion requested by the user."
                    }
                },
                "required": ["user_request"]
            }
        }
