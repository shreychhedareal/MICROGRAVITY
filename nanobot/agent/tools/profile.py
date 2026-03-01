"""Tool for managing the persistent User Psychological Profile."""

import os
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool

class UserProfileTool(Tool):
    """
    Tool to read and update the persistent User Profile.
    
    It maintains the user's motivations, visions, expectations, and ethical values 
    so the agent swarm understands *why* a user is requesting a task.
    """
    
    def __init__(self, workspace_path: str | Path):
        self._workspace = Path(workspace_path).expanduser().resolve()
        self._profile_file = self._workspace / "memory" / "PROFILE.md"
        
    @property
    def name(self) -> str:
        return "user_profile"
        
    @property
    def description(self) -> str:
        return (
            "Tool to manage the persistent psychological profile and long-term vision of the user. "
            "Action 'read': See the user's documented motives, expectations, value systems, and goals. "
            "Action 'append': Add a new learned motive or value system to the profile based on recent chats. "
            "Action 'write': Overwrite the entire profile with an updated structure."
        )
        
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "What to do with the Profile: 'read', 'append', or 'write'",
                    "enum": ["read", "append", "write"]
                },
                "content": {
                    "type": "string",
                    "description": "The text to append or write to the Profile. Required for 'append' and 'write'."
                }
            },
            "required": ["action"],
        }
        
    async def execute(self, action: str, content: str | None = None, **kwargs: Any) -> str:
        """Read, Write, or Append to PROFILE.md."""
        try:
            # Ensure workspace memory dir exists
            memory_dir = self._workspace / "memory"
            if not memory_dir.exists():
                memory_dir.mkdir(parents=True, exist_ok=True)
                
            if action == "read":
                if not self._profile_file.exists():
                    return "No User Profile exists yet. The PROFILE.md file is empty or missing."
                return self._profile_file.read_text(encoding="utf-8")
                
            elif action == "write":
                if not content:
                    return "Error: You must provide the 'content' argument when writing to the Profile."
                self._profile_file.write_text(content, encoding="utf-8")
                return f"Successfully completely overwritten the User Profile at {self._profile_file}"
                
            elif action == "append":
                if not content:
                    return "Error: You must provide the 'content' argument when appending to the Profile."
                with open(self._profile_file, "a", encoding="utf-8") as f:
                    f.write(f"\n{content}\n")
                return f"Successfully appended new psychological data/motives to the User Profile."
                
            else:
                return f"Error: Unknown action '{action}'."
                
        except Exception as e:
            return f"Error interacting with the User Profile: {e}"
