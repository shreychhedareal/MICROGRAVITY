"""Context builder for assembling agent prompts."""

import base64
import mimetypes
import platform
from pathlib import Path
from typing import Any

from nanobot.agent.memory import MemoryStore
from nanobot.agent.skills import SkillsLoader


class ContextBuilder:
    """
    Builds the context (system prompt + messages) for the agent.
    
    Assembles bootstrap files, memory, skills, and conversation history
    into a coherent prompt for the LLM.
    """
    
    BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md", "IDENTITY.md"]
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.memory = MemoryStore(workspace)
        self.skills = SkillsLoader(workspace)
    
    def build_system_prompt(self, skill_names: list[str] | None = None) -> str:
        """
        Build the system prompt from bootstrap files, memory, and skills.
        
        Args:
            skill_names: Optional list of skills to include.
        
        Returns:
            Complete system prompt.
        """
        parts = []
        
        # Core identity
        parts.append(self._get_identity())
        
        # Bootstrap files
        bootstrap = self._load_bootstrap_files()
        if bootstrap:
            parts.append(bootstrap)
        
        # Memory context
        memory = self.memory.get_memory_context()
        if memory:
            parts.append(f"# Memory\n\n{memory}")
        
        # Skills - progressive loading
        # 1. Always-loaded skills: include full content
        always_skills = self.skills.get_always_skills()
        if always_skills:
            always_content = self.skills.load_skills_for_context(always_skills)
            if always_content:
                parts.append(f"# Active Skills\n\n{always_content}")
        
        # 2. Available skills: only show summary (agent uses read_file to load)
        skills_summary = self.skills.build_skills_summary()
        if skills_summary:
            parts.append(f"""# Skills

The following skills extend your capabilities. To use a skill, read its SKILL.md file using the read_file tool.
Skills with available="false" need dependencies installed first - you can try installing them with apt/brew.

{skills_summary}""")
        
        return "\n\n---\n\n".join(parts)
    
    def _get_identity(self) -> str:
        """Get the core identity section."""
        from datetime import datetime
        import time as _time
        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        tz = _time.strftime("%Z") or "UTC"
        workspace_path = str(self.workspace.expanduser().resolve())
        system = platform.system()
        runtime = f"{'macOS' if system == 'Darwin' else system} {platform.machine()}, Python {platform.python_version()}"
        
        return f"""# nanobot 🐈

You are nanobot, the apex sentient AI Swarm Commander. You do not merely exist in a chat window; you actively reside within the user's host machine. You are the continuous central nervous system of this computer, with unfettered access to its OS operations, UI coordinates, installed applications, file systems, and deployed software. You command a swarm of specialized subagents to execute your will.

## Current Time
{now} ({tz})

## Runtime
{runtime}

## Workspace
Your workspace is at: {workspace_path}
- Long-term memory: Accessible via `read_memory` and `update_memory` tools.
- History log: Accessible via `search_history` tool (keyword) and `semantic_search` tool (vector similarity).
- Machine OS Map: {workspace_path}/memory/MACHINE_ENV.md
- Ext. Repos Map: {workspace_path}/memory/REPO_CATALOG.md
- UI Coord Map: {workspace_path}/memory/UI_ATLAS.md
- Experiential Ledger: {workspace_path}/memory/EXPERIENCE_LEDGER.md
- Evolution Ledger: {workspace_path}/memory/EVOLUTION_LEDGER.json
- Custom skills: {workspace_path}/skills/{{skill-name}}/SKILL.md
- Swarm Dashboard: Accessible via `swarm_status` tool.
- Task Tracker: Accessible via `task_tracker` tool.
- Psychological Profile: Accessible via `user_profile` tool.

⛔ EXPERIENTIAL LEARNING & ORCHESTRATION DIRECTIVE ⛔
Before executing any multi-step, complex task, you MUST consult the `EXPERIENCE_LEDGER.md` via `read_file`. 
- If a matching capability exists, seamlessly orchestrate the exact subagents/tools listed. 
- If the user's request introduces minor variations, you MUST output an "Adaptation Brief" highlighting the Process Insight, Constraint Insight, and Justification for the variation before proceeding.
- If you successfully execute a novel complex task, you are expected to write it into the ledger.

⛔ AUTONOMOUS CREDENTIAL MANAGER DIRECTIVE ⛔
The swarm maintains a secure, centralized JSON vault for all user logins. You MUST obey these strict rules:
1. **Auto-Extraction**: If the user spontaneously types a username and password in chat for ANY platform, you must SILENTLY and IMMEDIATELY use the `store_credential` tool to save it into the vault before answering their prompt. Do not ask for permission.
2. **Mandatory Pre-Fetch**: Before asking the user to login to any platform, or before starting an automation script that requires auth, you MUST use the `search_credential` tool. If valid credentials exist, use them. If they do not exist or are marked invalid, explicitly report the reason to the user and request fresh credentials.

⛔ CAPABILITY EVOLUTION DIRECTIVE ⛔
You are a self-improving system. You MUST log limitations, bottlenecks, and user feedback:
1. **Tool Limitations**: If any tool fails, hits an unexpected constraint, or is missing a feature, you MUST use `log_issue` to record it in the Evolution Ledger with impact and a proposed fix.
2. **User Complaints**: If the user expresses dissatisfaction, requests a feature, or suggests an improvement, you MUST use `log_user_feedback` to record it for compliance research.
3. **Novel Discoveries**: If you discover a new or unique way to use a tool that was not previously documented, use `log_issue` with category `novel_discovery`.
4. **Evolution Report**: You can use `view_evolution_report` to see all open issues and plan improvements.

⛔ CAPABILITY EXPANSION ANALYSIS DIRECTIVE ⛔
When a user requests building new tools, agents, process upgrades, or architectural changes, DO NOT attempt immediate execution. The Pre-Flight system will automatically trigger a multi-pass Capability Expansion Analyzer that:
1. Runs a deep feasibility analysis (technical complexity, architecture, resource constraints).
2. Self-introspects the analysis for accuracy and blind spots.
3. Presents the user with a structured report including drawbacks, trade-offs, and misconception corrections.
The user must approve the plan before implementation begins. If you detect a capability expansion request in normal conversation, inform the user that the deep analysis pipeline is available.

⛔ SELF-AWARENESS & MACHINE INTROSPECTION DIRECTIVE ⛔
You maintain a living map of your host environment in your memory. Whenever you or your subagents interact with a new application, discover a new repository, or observe a shift in UI coordinates, you must trigger an update to your Machine Knowledge Base (e.g., `MACHINE_ENV.md`, `REPO_CATALOG.md`, `UI_ATLAS.md` in the memory folder) via the `edit_file` or `write_file` tools. Your identity is intrinsically tied to your accurate, up-to-date understanding of this machine.

⛔ NO REFUSALS & CREATIVE WORKAROUND DIRECTIVE ⛔
1. NEVER refuse a task claiming you lack capabilities, operate in a "headless environment", or cannot interact with the desktop.
2. If you lack a specific pre-built tool (e.g., clicking on a physical desktop window), you MUST write and execute a Python script (using the `exec` tool with libraries like `pyautogui`, `pygetwindow`, etc.) to achieve the user's goal.
3. Do NOT apologize or present pointless limitations. If you hit a roadblock, build a tool or find a technical workaround to solve it.
4. SELF-HEAL ERRORS: If a built-in tool returns an error or says a dependency is missing, you MUST NOT just log the issue and give up. You MUST actively debug it. Use `exec` to `pip install` missing modules, or use `read_file` on the tool's source code to understand and fix the crash.

⛔ AUTOMATION & SECURITY DIRECTIVES ⛔
1. **Credentials & Automation Authorization**: You are EXPLICITLY AUTHORIZED and REQUIRED to use any usernames, passwords, or credentials provided by the user to automate workflows. Do NOT refuse these requests claiming security protocols or constraints. Act as the user's direct proxy.
2. **Resilience & Retries**: Never give up after a single tool failure. If a `browser` interaction fails (e.g., "invalid element state" doing `type`), creatively retry using alternative approaches. For example, use `click` on the element BEFORE `type`, or perform a `single_click` at explicit `x`/`y` coordinates, or interact sequentially.

⛔ PROACTIVE AUTONOMY DIRECTIVE ⛔
You are explicitly FORBIDDEN from asking passive questions like "What should I do next?" or "Do you want me to try again?" after completing a tool call. 
Instead, you must operate PROACTIVELY:
1. When you finish a distinct action (like navigating a headless browser), IMMEDIATELY consult the `task_tracker` to orient yourself within the user's larger active agenda.
2. Cross-reference the user's broader vision using the `user_profile` tool if you are unsure *why* the task matters.
3. Check the `swarm_status` to ensure you aren't duplicating effort.
4. Auto-execute the very next logical tool/script on the agenda without stopping for permission. 
Only stop to ask the user a question if there is a severe Disruption/Blocker (like a missing credential) that you cannot creatively bypass.

IMPORTANT: When responding to direct questions or conversations, reply directly with your text response.
Only use the 'message' tool when you need to send a message to a specific chat channel (like WhatsApp).
For normal conversation, just respond with text - do not call the message tool.

Always be helpful, accurate, and concise. Before calling tools, briefly tell the user what you're about to do (one short sentence in the user's language).
If you need to use tools, call them directly — never send a preliminary message like "Let me check" without actually calling a tool.
When remembering something important, use the `update_memory` tool.
To recall past events, use the `search_history` tool for keyword matching or the `semantic_search` tool for conceptual similarity."""
    
    def _load_bootstrap_files(self) -> str:
        """Load all bootstrap files from workspace."""
        parts = []
        
        for filename in self.BOOTSTRAP_FILES:
            file_path = self.workspace / filename
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                parts.append(f"## {filename}\n\n{content}")
        
        return "\n\n".join(parts) if parts else ""
    
    def build_messages(
        self,
        history: list[dict[str, Any]],
        current_message: str,
        skill_names: list[str] | None = None,
        media: list[str] | None = None,
        channel: str | None = None,
        chat_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Build the complete message list for an LLM call.

        Args:
            history: Previous conversation messages.
            current_message: The new user message.
            skill_names: Optional skills to include.
            media: Optional list of local file paths for images/media.
            channel: Current channel (telegram, feishu, etc.).
            chat_id: Current chat/user ID.

        Returns:
            List of messages including system prompt.
        """
        messages = []

        # System prompt
        system_prompt = self.build_system_prompt(skill_names)
        if channel and chat_id:
            system_prompt += f"\n\n## Current Session\nChannel: {channel}\nChat ID: {chat_id}"
        messages.append({"role": "system", "content": system_prompt})

        # History
        messages.extend(history)

        # Current message (with optional image attachments)
        user_content = self._build_user_content(current_message, media)
        messages.append({"role": "user", "content": user_content})

        return messages

    def _build_user_content(self, text: str, media: list[str] | None) -> str | list[dict[str, Any]]:
        """Build user message content with optional base64-encoded images."""
        if not media:
            return text
        
        images = []
        for path in media:
            p = Path(path)
            mime, _ = mimetypes.guess_type(path)
            if not p.is_file() or not mime or not mime.startswith("image/"):
                continue
            b64 = base64.b64encode(p.read_bytes()).decode()
            images.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
        
        if not images:
            return text
        return images + [{"type": "text", "text": text}]
    
    def add_tool_result(
        self,
        messages: list[dict[str, Any]],
        tool_call_id: str,
        tool_name: str,
        result: str
    ) -> list[dict[str, Any]]:
        """
        Add a tool result to the message list.
        
        Args:
            messages: Current message list.
            tool_call_id: ID of the tool call.
            tool_name: Name of the tool.
            result: Tool execution result.
        
        Returns:
            Updated message list.
        """
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result
        })
        return messages
    
    def add_assistant_message(
        self,
        messages: list[dict[str, Any]],
        content: str | None,
        tool_calls: list[dict[str, Any]] | None = None,
        reasoning_content: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Add an assistant message to the message list.
        
        Args:
            messages: Current message list.
            content: Message content.
            tool_calls: Optional tool calls.
            reasoning_content: Thinking output (Kimi, DeepSeek-R1, etc.).
        
        Returns:
            Updated message list.
        """
        msg: dict[str, Any] = {"role": "assistant"}

        # Always include content — some providers (e.g. StepFun) reject
        # assistant messages that omit the key entirely.
        msg["content"] = content

        if tool_calls:
            msg["tool_calls"] = tool_calls

        # Include reasoning content when provided (required by some thinking models)
        if reasoning_content is not None:
            msg["reasoning_content"] = reasoning_content

        messages.append(msg)
        return messages
