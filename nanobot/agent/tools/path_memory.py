"""Contextual Path Memory tools."""

import json
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool
from nanobot.agent.memory import MemoryStore

class BookmarkPathTool(Tool):
    """Tool to bookmark an absolute path with description into the Path Ledger."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.store = MemoryStore(workspace)

    @property
    def name(self) -> str:
        return "bookmark_path"

    @property
    def description(self) -> str:
        return "Bookmarks an absolute internal file path with a semantic description so that the Swarm remembers where core system concepts are located."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "absolute_path": {
                    "type": "string",
                    "description": "The absolute path to the file or folder."
                },
                "semantic_description": {
                    "type": "string",
                    "description": "What is this file for? E.g., 'Main database schema definition' or 'The core LLM prompt loop'."
                }
            },
            "required": ["absolute_path", "semantic_description"]
        }

    async def execute(self, absolute_path: str, semantic_description: str, **kwargs: Any) -> str:
        data = {}
        content = self.store.read_text("PATH_LEDGER.json")
        if content:
            try:
                data = json.loads(content)
            except Exception:
                pass
                
        # We index by path to prevent duplicates
        data[absolute_path] = semantic_description
        
        self.store.write_text("PATH_LEDGER.json", json.dumps(data, indent=2))
        
        return f"Successfully bookmarked path '{absolute_path}'."


class RecallPathsTool(Tool):
    """Tool to read the bookmarked Path Ledger."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.store = MemoryStore(workspace)

    @property
    def name(self) -> str:
        return "recall_paths"

    @property
    def description(self) -> str:
        return "Reads the Path Ledger to retrieve all bookmarked files and their semantic descriptions. Highly useful when navigating a large codebase."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, **kwargs: Any) -> str:
        content = self.store.read_text("PATH_LEDGER.json")
        if not content:
            return "The Path Ledger is currently empty. No bookmarks exist."
            
        try:
            data = json.loads(content)
            if not data:
                return "The Path Ledger is currently empty."
                
            lines = ["--- PATH LEDGER ---"]
            for path, desc in data.items():
                lines.append(f"[{desc}]\n{path}\n")
                
            return "\n".join(lines)
        except Exception as e:
            return f"Failed to read Path Ledger: {str(e)}"
