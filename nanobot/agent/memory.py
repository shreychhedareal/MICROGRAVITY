"""Memory system for persistent agent memory."""

from __future__ import annotations

import json
import lmdb
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from nanobot.utils.helpers import ensure_dir
from nanobot.agent.vectorstore import VectorMemory

if TYPE_CHECKING:
    from nanobot.providers.base import LLMProvider
    from nanobot.session.manager import Session


_SAVE_MEMORY_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Save the memory consolidation result to persistent storage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "history_entry": {
                        "type": "string",
                        "description": "A paragraph (2-5 sentences) summarizing key events/decisions/topics. "
                        "Start with [YYYY-MM-DD HH:MM]. Include detail useful for grep search.",
                    },
                    "memory_update": {
                        "type": "string",
                        "description": "Full updated long-term memory as markdown. Include all existing "
                        "facts plus new ones. Return unchanged if nothing new.",
                    },
                },
                "required": ["history_entry", "memory_update"],
            },
        },
    }
]


class MemoryStore:
    """Two-layer persistent memory: Long-term facts + Append-only history, backed purely by LMDB."""

    def __init__(self, workspace: Path, map_size: int = 10485760):
        self.workspace = workspace
        self.memory_dir = ensure_dir(workspace / "memory")
        self.lmdb_path = str(self.memory_dir / "lmdb_store")
        # map_size is 10MB by default, plenty for text md config
        self.env = lmdb.open(self.lmdb_path, map_size=map_size, create=True)
        # Vector store for semantic search
        self.vector = VectorMemory(workspace)

    def read_text(self, key: str) -> str:
        with self.env.begin() as txn:
            val = txn.get(key.encode("utf-8"))
            if val is not None:
                return val.decode("utf-8")
        return ""

    def write_text(self, key: str, content: str) -> None:
        with self.env.begin(write=True) as txn:
            txn.put(key.encode("utf-8"), content.encode("utf-8"))

    def append_text(self, key: str, content: str, delimiter: str = "\n") -> None:
        with self.env.begin(write=True) as txn:
            k = key.encode("utf-8")
            val = txn.get(k)
            curr = val.decode("utf-8") if val else ""
            new_val = (curr + delimiter + content) if curr else content
            txn.put(k, new_val.encode("utf-8"))

    def read_long_term(self) -> str:
        return self.read_text("MEMORY") or self.read_text("MEMORY.md") or ""

    def write_long_term(self, content: str, labels: list[str] | None = None) -> None:
        self.write_text("MEMORY", content)
        # Also index into vector store for semantic retrieval with optional labels
        self.vector.add_longterm(content, labels=labels)

    def append_history(self, entry: str, labels: list[str] | None = None) -> None:
        """Append an entry to the history log.

        These should be timestamped events representing raw interaction flow.
        Also automatically indexed into the local vector store for semantic search.
        """
        self.append_text("HISTORY", entry.rstrip() + "\n", delimiter="\n")
        # Also index into vector store for semantic clustering
        self.vector.add_history(entry, labels=labels)

    def search_history(self, query: str) -> str:
        history = self.read_text("HISTORY") or self.read_text("HISTORY.md") or ""
        lines = history.splitlines()
        q = query.lower()
        results = [line for line in lines if q in line.lower()]
        return "\n".join(results)

    def semantic_search_history(self, query: str, n_results: int = 5, labels: list[str] | None = None) -> list[str]:
        """Search history log embedding indices for conceptual matches.
        
        Args:
            query: The conceptual query string.
            n_results: Maximum number of history entries to return.
            labels: Optional filter for categorical label clusters.
            
        Returns:
            List of matching history entry strings.
        """
        return self.vector.search_history(query, n_results, labels=labels)

    def semantic_search_memory(self, query: str, n_results: int = 5, labels: list[str] | None = None) -> list[str]:
        """Semantic similarity search over long-term memory chunks, with optional category labels."""
        return self.vector.search_longterm(query, n_results, labels=labels)

    # ── Consequence Storage ──────────────────────────────────────────

    def store_consequence(
        self,
        summary: str,
        domain_labels: list[str] | None = None,
    ) -> None:
        """Store an important task outcome in the most reusable form.

        Consequences are indexed into the vector store with a ``consequence``
        label plus any additional domain labels so they can be recalled
        instantly for future decision-making.

        Args:
            summary: A concise, structured summary of the outcome.
            domain_labels: Additional domain tags (e.g., ``["api", "auth"]``).
        """
        labels = ["consequence"] + (domain_labels or [])
        self.vector.add_longterm(summary, labels=labels)

    def recall_consequences(
        self,
        query: str,
        domain_labels: list[str] | None = None,
        n_results: int = 5,
    ) -> list[str]:
        """Retrieve past consequential outcomes relevant to a query.

        Always filters to the ``consequence`` cluster. Additional domain
        labels further narrow the search scope.

        Args:
            query: Natural language description of what you need.
            domain_labels: Optional extra domain filters.
            n_results: Maximum results to return.

        Returns:
            List of matching consequence summaries.
        """
        labels = ["consequence"] + (domain_labels or [])
        return self.vector.search_longterm(query, n_results, labels=labels)

    def get_memory_context(self) -> str:
        long_term = self.read_long_term()
        return f"## Long-term Memory\n{long_term}" if long_term else ""

    async def consolidate(
        self,
        session: Session,
        provider: LLMProvider,
        model: str,
        *,
        archive_all: bool = False,
        memory_window: int = 50,
    ) -> None:
        """Consolidate old messages into long-term memory + history via LLM tool call."""
        if archive_all:
            old_messages = session.messages
            keep_count = 0
            logger.info("Memory consolidation (archive_all): {} messages", len(session.messages))
        else:
            keep_count = memory_window // 2
            if len(session.messages) <= keep_count:
                return
            if len(session.messages) - session.last_consolidated <= 0:
                return
            old_messages = session.messages[session.last_consolidated:-keep_count]
            if not old_messages:
                return
            logger.info("Memory consolidation: {} to consolidate, {} keep", len(old_messages), keep_count)

        lines = []
        for m in old_messages:
            if not m.get("content"):
                continue
            tools = f" [tools: {', '.join(m['tools_used'])}]" if m.get("tools_used") else ""
            lines.append(f"[{m.get('timestamp', '?')[:16]}] {m['role'].upper()}{tools}: {m['content']}")

        current_memory = self.read_long_term()
        prompt = f"""Process this conversation and call the save_memory tool with your consolidation.

## Current Long-term Memory
{current_memory or "(empty)"}

## Conversation to Process
{chr(10).join(lines)}"""

        try:
            response = await provider.chat(
                messages=[
                    {"role": "system", "content": "You are a memory consolidation agent. Call the save_memory tool with your consolidation of the conversation."},
                    {"role": "user", "content": prompt},
                ],
                tools=_SAVE_MEMORY_TOOL,
                model=model,
            )

            if not response.has_tool_calls:
                logger.warning("Memory consolidation: LLM did not call save_memory, skipping")
                return

            args = response.tool_calls[0].arguments
            if entry := args.get("history_entry"):
                if not isinstance(entry, str):
                    entry = json.dumps(entry, ensure_ascii=False)
                self.append_history(entry)
            if update := args.get("memory_update"):
                if not isinstance(update, str):
                    update = json.dumps(update, ensure_ascii=False)
                if update != current_memory:
                    self.write_long_term(update)

            session.last_consolidated = 0 if archive_all else len(session.messages) - keep_count
            logger.info("Memory consolidation done: {} messages, last_consolidated={}", len(session.messages), session.last_consolidated)
        except Exception as e:
            logger.error("Memory consolidation failed: {}", e)
