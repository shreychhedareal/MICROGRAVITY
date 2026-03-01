import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("nanobot.context_tree")

class ContextTreeBuilder:
    """
    Intelligently scrapes the Swarm's environment, memory, and active tasks 
    to build a high-density, low-token Context Tree for the Intent Analyzer.
    """
    
    def __init__(self, workspace_path: Path | str, subagents=None):
        self._workspace = Path(workspace_path).expanduser().resolve()
        self.subagents = subagents
        
    async def build(self, session: Any = None) -> Dict[str, str]:
        """Gathers all dynamic context and returns a dictionary of formatted strings."""
        
        return {
            "history_str": self._get_history(session),
            "profile_str": self._get_profile(),
            "swarm_status_str": await self._get_swarm_status(),
            "active_tasks_str": await self._get_active_tasks()
        }
        
    def _get_history(self, session: Any) -> str:
        history_str = "No recent conversation history."
        if session and hasattr(session, "get_history"):
            history = session.get_history(max_messages=10)
            if history:
                history_lines = []
                for msg in history:
                    role = msg.get("role", "unknown").upper()
                    content = msg.get("content", "")
                    if len(content) > 300:
                        content = content[:300] + "... [truncated]"
                    history_lines.append(f"{role}: {content}")
                history_str = "\n".join(history_lines)
        return history_str
        
    def _get_profile(self) -> str:
        profile_path = self._workspace / "memory" / "PROFILE.md"
        if profile_path.exists():
            return profile_path.read_text(encoding="utf-8")
        return "No profile exists yet."
        
    async def _get_swarm_status(self) -> str:
        if not self.subagents:
            return "Swarm Status: Unknown (No Subagent Manager linked)"
            
        count = self.subagents.get_running_count()
        if count == 0:
            return "Swarm Status: IDLE. No active background subagents."
            
        active = self.subagents.get_active_subagents()
        lines = [f"Swarm Status: BUSY ({count} active subagents)"]
        for t_id, t_desc in active.items():
            lines.append(f"- [{t_id}]: {t_desc}")
            
        return "\n".join(lines)
        
    async def _get_active_tasks(self) -> str:
        # Check task tree
        task_file = self._workspace / "workspace" / "tasks.json"
        if not task_file.exists():
            return "Task Tree: No formal tasks currently tracked."
            
        try:
            import json
            data = json.loads(task_file.read_text(encoding="utf-8"))
            tasks = data.get("tasks", [])
            if not tasks:
                return "Task Tree: Empty."
                
            in_progress = [t for t in tasks if t.get("status") == "in_progress"]
            pending = [t for t in tasks if t.get("status") == "pending"]
            
            lines = []
            if in_progress:
                lines.append("ACTIVE TASKS:")
                for t in in_progress:
                    lines.append(f"- {t.get('title')} (Priority: {t.get('priority')})")
            if pending:
                lines.append(f"PENDING TASKS: {len(pending)} items waiting.")
                
            return "\n".join(lines) if lines else "Task Tree: No active/pending tasks."
        except Exception as e:
            return f"Task Tree: Error reading tasks ({e})"
