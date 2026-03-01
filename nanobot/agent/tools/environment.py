"""Environment variable management tools."""

import os
from typing import Any

from nanobot.agent.tools.base import Tool


class ReadEnvVarTool(Tool):
    """Tool to read environment variables."""

    @property
    def name(self) -> str:
        return "read_env_var"

    @property
    def description(self) -> str:
        return "Reads the value of an environment variable. Useful for finding paths, tokens, or system configurations."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "var_name": {
                    "type": "string",
                    "description": "The name of the environment variable (e.g., 'PATH', 'USERPROFILE')"
                }
            },
            "required": ["var_name"]
        }

    async def execute(self, var_name: str, **kwargs: Any) -> str:
        value = os.environ.get(var_name)
        if value is None:
            return f"Environment variable '{var_name}' is not set."
        return f"Environment variable '{var_name}':\n{value}"


class SetEnvVarTool(Tool):
    """Tool to set environment variables for the current process."""

    @property
    def name(self) -> str:
        return "set_env_var"

    @property
    def description(self) -> str:
        return "Sets an environment variable for the agent's current running process. This will affect subsequent tools run in this session."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "var_name": {
                    "type": "string",
                    "description": "The name of the environment variable to set."
                },
                "value": {
                    "type": "string",
                    "description": "The value to assign."
                }
            },
            "required": ["var_name", "value"]
        }

    async def execute(self, var_name: str, value: str, **kwargs: Any) -> str:
        os.environ[var_name] = value
        return f"Successfully set environment variable '{var_name}'."
