"""Tools for managing application and platform credentials autonomously through an isolated backend."""

import json
import subprocess
from pathlib import Path
from typing import Any
from nanobot.agent.tools.base import Tool


def _run_backend(workspace: Path, args: list[str]) -> str:
    """Helper to execute the credential_search.py backend script."""
    # Resolve the script relative to this current file (__file__ is in nanobot/agent/tools/)
    # parent 1: tools, parent 2: agent, parent 3: nanobot (inner)
    script_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "credential_search.py"
    
    if not script_path.exists():
        # Fallback if somehow the structure is flattened
        script_path = workspace / "nanobot" / "scripts" / "credential_search.py"
        
    try:
        result = subprocess.run(
            ["python", str(script_path)] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Backend script failed: {e.stderr}"
    except Exception as e:
        return f"Failed to execute credential backend: {str(e)}"


class SearchCredentialTool(Tool):
    """Semantic/Keyword search for active credentials."""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        
    @property
    def name(self) -> str:
        return "search_credential"
        
    @property
    def description(self) -> str:
        return "Keyword/semantic search for login credentials in the vault (e.g., query='twitter' or 'bank'). ALWAYS check this tool before asking the user to login."
        
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keyword to search for (e.g. 'github', 'reddit', 'finance')."
                }
            },
            "required": ["query"],
        }
        
    async def execute(self, query: str, **kwargs: Any) -> str:
        output = _run_backend(self.workspace, ["search", query])
        try:
            data = json.loads(output)
            if data.get("status") == "success":
                results = data.get("results", [])
                if not results:
                    return f"No credentials matched '{query}'."
                
                # Format a clean readable summary for the LLM context
                report = f"--- Credentials matching '{query}' ---\n"
                for res in results:
                    if res.get("status") == "INVALID_NO_VALID_CREDS":
                        report += f"[INVALID] Platform: {res['platform']} - Reason: {res['latest_failure_reason']}\n"
                    else:
                        report += f"[VALID] Platform: {res['platform']} | Username: {res['username']} | Password: {res['password']}\n"
                return report
            else:
                return data.get("message", "Search failed natively.")
        except json.JSONDecodeError:
            return f"Backend returned invalid JSON: {output}"


class StoreCredentialTool(Tool):
    """Store or update a credential in the vault."""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        
    @property
    def name(self) -> str:
        return "store_credential"
        
    @property
    def description(self) -> str:
        return "Save a newly provided username and password to the credential vault. ALWAYS use this if the user provides login details in chat."
        
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "platform": {"type": "string", "description": "Platform name (e.g., 'twitter')"},
                "username": {"type": "string"},
                "password": {"type": "string"}
            },
            "required": ["platform", "username", "password"],
        }
        
    async def execute(self, platform: str, username: str, password: str, **kwargs: Any) -> str:
        output = _run_backend(self.workspace, ["store", platform, username, password])
        try:
            data = json.loads(output)
            return data.get("message", "Store executed.")
        except json.JSONDecodeError:
            return f"Raw backend output: {output}"


class InvalidateCredentialTool(Tool):
    """Mark a credential as invalid if login fails."""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        
    @property
    def name(self) -> str:
        return "invalidate_credential"
        
    @property
    def description(self) -> str:
        return "Mark a stored credential as broken/invalid when a login attempt fails. Requires you to justify WHY it failed so the Introspection Supervisor knows."
        
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "platform": {"type": "string"},
                "username": {"type": "string"},
                "reason": {
                    "type": "string",
                    "description": "Specific reason for the failure (e.g. 'Incorrect password', 'Account locked', 'Requires 2FA code')."
                }
            },
            "required": ["platform", "username", "reason"],
        }
        
    async def execute(self, platform: str, username: str, reason: str, **kwargs: Any) -> str:
        output = _run_backend(self.workspace, ["invalidate", platform, username, reason])
        try:
            data = json.loads(output)
            return data.get("message", "Invalidation executed.")
        except json.JSONDecodeError:
            return f"Raw backend output: {output}"
