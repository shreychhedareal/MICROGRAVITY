"""Diagnostic tools allowing the agent to read its own logs."""

from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool


class ReadLogsTool(Tool):
    """Tool to read the agent's internal diagnostic logs."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.log_dir = workspace / "logs"

    @property
    def name(self) -> str:
        return "read_logs"

    @property
    def description(self) -> str:
        return "Reads the agent's internal diagnostic logs. Very useful for self-healing: use this to figure out why an internal tool crashed (check 'errors.log') or why a network request failed (check 'network.log')."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "log_type": {
                    "type": "string",
                    "description": "Which log to read: 'errors', 'network', or 'analysis'.",
                    "enum": ["errors", "network", "analysis"]
                },
                "lines": {
                    "type": "integer",
                    "description": "Number of recent lines to read. Defaults to 50."
                }
            },
            "required": ["log_type"]
        }

    async def execute(self, log_type: str, lines: int = 50, **kwargs: Any) -> str:
        filename = f"{log_type}.log"
        filepath = self.log_dir / filename
        
        if not filepath.exists():
            return f"The log file '{filename}' is currently empty or does not exist."
            
        try:
            content = filepath.read_text(encoding="utf-8")
            all_lines = content.strip().split("\n")
            
            if not all_lines or (len(all_lines) == 1 and not all_lines[0]):
                return f"[{filename}] is empty."
                
            recent_lines = all_lines[-lines:]
            
            report = [f"--- RECENT {len(recent_lines)} LINES OF {filename} ---"]
            report.extend(recent_lines)
            
            return "\n".join(report)
        except Exception as e:
            return f"Failed to read diagnostic log: {str(e)}"
