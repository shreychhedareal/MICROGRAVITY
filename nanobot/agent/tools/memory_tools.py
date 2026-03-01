"""Memory interaction tools: read, search, update."""

from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool
from nanobot.agent.memory import MemoryStore

class SearchHistoryTool(Tool):
    """Tool to search the append-only history log (LMDB)."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.store = MemoryStore(workspace)

    @property
    def name(self) -> str:
        return "search_history"

    @property
    def description(self) -> str:
        return "Search the history log for a specific keyword or phrase."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The text to search for in the history log"
                }
            },
            "required": ["query"]
        }

    async def execute(self, query: str, **kwargs: Any) -> str:
        try:
            results = self.store.search_history(query)
            if not results:
                return f"No matches found for '{query}' in history."
            return results
        except Exception as e:
            return f"Error searching history: {str(e)}"

class UpdateMemoryTool(Tool):
    """Tool to overwrite the long-term memory (LMDB)."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.store = MemoryStore(workspace)

    @property
    def name(self) -> str:
        return "update_memory"

    @property
    def description(self) -> str:
        return "Overwrite the entire long-term memory with new content. Ensure you include all existing important facts along with new ones."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The complete new markdown content for long-term memory"
                }
            },
            "required": ["content"]
        }

    async def execute(self, content: str, **kwargs: Any) -> str:
        try:
            self.store.write_long_term(content)
            return "Successfully updated long-term memory."
        except Exception as e:
            return f"Error updating memory: {str(e)}"

class ReadMemoryTool(Tool):
    """Tool to read the current long-term memory."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.store = MemoryStore(workspace)

    @property
    def name(self) -> str:
        return "read_memory"

    @property
    def description(self) -> str:
        return "Read the current contents of the long-term memory."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, **kwargs: Any) -> str:
        try:
            content = self.store.read_long_term()
            return content or "(Memory is currently empty)"
        except Exception as e:
            return f"Error reading memory: {str(e)}"

class SemanticSearchTool(Tool):
    """Tool for semantic (vector similarity) search over history and memory."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.store = MemoryStore(workspace)

    @property
    def name(self) -> str:
        return "semantic_search"

    @property
    def description(self) -> str:
        return (
            "Search memory using semantic similarity (vector search). "
            "Returns conceptually related results even if exact keywords don't match. "
            "Use 'collection' to choose between 'history' (past events) and 'memory' (long-term facts)."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query to search for"
                },
                "collection": {
                    "type": "string",
                    "enum": ["history", "memory"],
                    "description": "Which collection to search: 'history' for past events, 'memory' for long-term facts"
                },
                "n_results": {
                    "type": "integer",
                    "description": "Number of results to return (default 5)",
                    "default": 5
                },
                "labels": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Optional list of categorical labels to restrict the search to specific clusters"
                }
            },
            "required": ["query", "collection"]
        }

    async def execute(self, query: str, collection: str = "history", n_results: int = 5, labels: list[str] | None = None, **kwargs: Any) -> str:
        try:
            if collection == "history":
                results = self.store.semantic_search_history(query, n_results, labels=labels)
            elif collection == "memory":
                results = self.store.semantic_search_memory(query, n_results, labels=labels)
            else:
                return f"Unknown collection '{collection}'. Use 'history' or 'memory'."

            if not results:
                return f"No semantically similar results found for '{query}' in {collection}."
            return "\n---\n".join(results)
        except Exception as e:
            return f"Error during semantic search: {str(e)}"
