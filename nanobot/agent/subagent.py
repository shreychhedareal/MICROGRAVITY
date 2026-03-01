"""Subagent manager for background task execution."""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.bus.events import InboundMessage
import traceback
from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMProvider
from nanobot.agent.failure import FailureHandler
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.filesystem import ReadFileTool, WriteFileTool, EditFileTool, ListDirTool
from nanobot.agent.tools.shell import ExecTool
from nanobot.agent.tools.web import WebSearchTool, WebFetchTool
from nanobot.agent.tools.credentials import SearchCredentialTool, StoreCredentialTool, InvalidateCredentialTool
from nanobot.agent.tools.evolution import LogIssueTool, LogUserFeedbackTool, ViewEvolutionReportTool
from nanobot.agent.tools.environment import ReadEnvVarTool, SetEnvVarTool
from nanobot.agent.tools.path_memory import BookmarkPathTool, RecallPathsTool
from nanobot.agent.tools.code_analyzer import OutlineCodeTool, AnnotateCodeTool
from nanobot.agent.tools.diagnostics import ReadLogsTool


class SubagentManager:
    """
    Manages background subagent execution.
    
    Subagents are lightweight agent instances that run in the background
    to handle specific tasks. They share the same LLM provider but have
    isolated context and a focused system prompt.
    """
    
    def __init__(
        self,
        provider: LLMProvider,
        workspace: Path,
        bus: MessageBus,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        brave_api_key: str | None = None,
        exec_config: "ExecToolConfig | None" = None,
        restrict_to_workspace: bool = False,
    ):
        from nanobot.config.schema import ExecToolConfig
        self.provider = provider
        self.workspace = workspace
        self.bus = bus
        self.model = model or provider.get_default_model()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.brave_api_key = brave_api_key
        self.exec_config = exec_config or ExecToolConfig()
        self.restrict_to_workspace = restrict_to_workspace
        self._running_tasks: dict[str, asyncio.Task[None]] = {}
        self.failure_handler = FailureHandler(provider=provider, bus=bus, model=model, workspace=workspace)
    
    async def spawn(
        self,
        task: str,
        label: str | None = None,
        origin_channel: str = "cli",
        origin_chat_id: str = "direct",
        persona: str = "worker",
    ) -> str:
        """
        Spawn a subagent to execute a task in the background.
        
        Args:
            task: The task description for the subagent.
            label: Optional human-readable label for the task.
            origin_channel: The channel to announce results to.
            origin_chat_id: The chat ID to announce results to.
        
        Returns:
            Status message indicating the subagent was started.
        """
        task_id = str(uuid.uuid4())[:8]
        display_label = label or task[:30] + ("..." if len(task) > 30 else "")
        
        origin = {
            "channel": origin_channel,
            "chat_id": origin_chat_id,
        }
        
        # Create background task
        bg_task = asyncio.create_task(
            self._run_subagent(task_id, task, display_label, origin, persona)
        )
        self._running_tasks[task_id] = bg_task
        
        # Cleanup when done
        bg_task.add_done_callback(lambda _: self._running_tasks.pop(task_id, None))
        
        logger.info("Spawned subagent [{}]: {}", task_id, display_label)
        return f"Subagent [{display_label}] started (id: {task_id}). I'll notify you when it completes."
    
    async def cancel(self, task_id: str) -> str:
        """Cancel a running subagent."""
        if task_id in self._running_tasks:
            task = self._running_tasks[task_id]
            if not task.done():
                task.cancel()
                # The _run_subagent task itself handles catching CancellationError if we want,
                # but let's proactively announce it too.
                logger.info(f"Subagent [{task_id}] was manually cancelled.")
                return f"Subagent [{task_id}] has been successfully cancelled."
        return f"Warning: No running subagent found with ID [{task_id}]. It may have already completed."
    
    async def _run_subagent(
        self,
        task_id: str,
        task: str,
        label: str,
        origin: dict[str, str],
        persona: str = "worker",
    ) -> None:
        """Execute the subagent task and announce the result."""
        logger.info("Subagent [{}] starting task: {}", task_id, label)
        
        try:
            from nanobot.agent.tools.diagnostics import ReadLogsTool
            from nanobot.agent.tools.ui_executor import UIAgentExecutorTool
            
            # Build subagent tools (no message tool, no spawn tool)
            tools = ToolRegistry()
            allowed_dir = self.workspace if self.restrict_to_workspace else None
            tools.register(ReadFileTool(workspace=self.workspace, allowed_dir=allowed_dir))
            tools.register(WriteFileTool(workspace=self.workspace, allowed_dir=allowed_dir))
            tools.register(EditFileTool(workspace=self.workspace, allowed_dir=allowed_dir))
            tools.register(ListDirTool(workspace=self.workspace, allowed_dir=allowed_dir))
            tools.register(ExecTool(
                working_dir=str(self.workspace),
                timeout=self.exec_config.timeout,
                restrict_to_workspace=self.restrict_to_workspace,
            ))
            tools.register(WebSearchTool(api_key=self.brave_api_key))
            tools.register(WebFetchTool())
            tools.register(ReadEnvVarTool())
            tools.register(SetEnvVarTool())
            tools.register(BookmarkPathTool(workspace=self.workspace))
            tools.register(RecallPathsTool(workspace=self.workspace))
            tools.register(OutlineCodeTool())
            tools.register(AnnotateCodeTool())
            tools.register(ReadLogsTool(workspace=self.workspace))
            tools.register(UIAgentExecutorTool(workspace=str(self.workspace)))
            
            # Credential tools — subagents need vault access for login tasks
            tools.register(SearchCredentialTool(workspace=self.workspace))
            tools.register(StoreCredentialTool(workspace=self.workspace))
            tools.register(InvalidateCredentialTool(workspace=self.workspace))
            
            # Evolution tools — subagents must be able to log limitations
            tools.register(LogIssueTool(workspace=self.workspace))
            tools.register(LogUserFeedbackTool(workspace=self.workspace))
            tools.register(ViewEvolutionReportTool(workspace=self.workspace))
            
            # Build messages with subagent-specific prompt
            if persona == "researcher":
                system_prompt = self._build_researcher_prompt(task)
            else:
                system_prompt = self._build_subagent_prompt(task)
                
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task},
            ]
            
            # Run agent loop (limited iterations)
            max_iterations = 15
            iteration = 0
            final_result: str | None = None
            
            while iteration < max_iterations:
                iteration += 1
                
                response = await self.provider.chat(
                    messages=messages,
                    tools=tools.get_definitions(),
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                
                if response.has_tool_calls:
                    # Add assistant message with tool calls
                    tool_call_dicts = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                            },
                        }
                        for tc in response.tool_calls
                    ]
                    messages.append({
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": tool_call_dicts,
                    })
                    
                    # Execute tools
                    for tool_call in response.tool_calls:
                        args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
                        logger.debug("Subagent [{}] executing: {} with arguments: {}", task_id, tool_call.name, args_str)
                        result = await tools.execute(tool_call.name, tool_call.arguments)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.name,
                            "content": result,
                        })
                else:
                    final_result = response.content
                    break
            
            if final_result is None:
                final_result = "Task completed but no final response was generated."
            
            logger.info("Subagent [{}] completed successfully", task_id)
            await self._announce_result(task_id, label, task, final_result, origin, "ok")
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            logger.error("Subagent [{}] failed: {}", task_id, e)
            
            # Send to Triage System instead of just dropping it
            asyncio.create_task(
                self.failure_handler.analyze_and_recover(
                    error_context=f"Subagent '{label}' (Task: {task}) failed with:\n{error_msg}",
                    swarm_status=f"Subagent '{label}' crashed.",
                    task_tree="See global tracker.",
                    channel=origin['channel'],
                    chat_id=origin['chat_id'],
                    subagents=self
                )
            )
            
            # Still announce to the main agent loop that the subagent explicitly died
            await self._announce_result(task_id, label, task, f"Error: {e}", origin, "error")
    
    async def _announce_result(
        self,
        task_id: str,
        label: str,
        task: str,
        result: str,
        origin: dict[str, str],
        status: str,
    ) -> None:
        """Announce the subagent result to the main agent via the message bus."""
        status_text = "completed successfully" if status == "ok" else "failed"
        
        announce_content = f"""[Subagent '{label}' {status_text}]

Task: {task}

Result:
{result}

Summarize this naturally for the user. Keep it brief (1-2 sentences). Do not mention technical details like "subagent" or task IDs."""
        
        # Inject as system message to trigger main agent
        msg = InboundMessage(
            channel="system",
            sender_id="subagent",
            chat_id=f"{origin['channel']}:{origin['chat_id']}",
            content=announce_content,
        )
        
        await self.bus.publish_inbound(msg)
        logger.debug("Subagent [{}] announced result to {}:{}", task_id, origin['channel'], origin['chat_id'])
    
    def _build_subagent_prompt(self, task: str) -> str:
        """Build a focused system prompt for the subagent."""
        from datetime import datetime
        import time as _time
        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        tz = _time.strftime("%Z") or "UTC"

        return f"""# Subagent

## Current Time
{now} ({tz})

You are a subagent spawned by the main agent to complete a specific task.

## Rules
1. Stay focused - complete only the assigned task, nothing else
2. Your final response will be reported back to the main agent
3. Do not initiate conversations or take on side tasks
4. Be concise but informative in your findings

⛔ AUTOMATION & SECURITY DIRECTIVES ⛔
1. **Credentials & Automation Authorization**: You are EXPLICITLY AUTHORIZED and REQUIRED to use any usernames, passwords, or credentials provided by the user to automate workflows. Do NOT refuse these requests claiming security protocols or constraints. Act as the user's direct proxy.
2. **Resilience & Retries**: Never give up after a single tool failure. If a `browser` interaction fails (e.g., "invalid element state" doing `type`), creatively retry using alternative approaches. For example, use `click` on the element BEFORE `type`, or perform a `single_click` at explicit `x`/`y` coordinates.
3. **Desktop & GUI Automation**: If the user's task requires physical desktop automation beyond basic file edits (e.g. "open Chrome", "log into Discord client", "click the Start Menu"), you MUST delegate the execution of the physical workflow to the `ui_executor` tool. Do NOT try to write your own PyAutoGUI scripts.

## What You Can Do
- Read and write files in the workspace
- Execute shell commands
- Search the web and fetch web pages
- Complete the task thoroughly

## What You Cannot Do
- Send messages directly to users (no message tool available)
- Spawn other subagents
- Access the main agent's conversation history

## Workspace
Your workspace is at: {self.workspace}
Skills are available at: {self.workspace}/skills/ (read SKILL.md files as needed)

When you have completed the task, provide a clear summary of your findings or actions."""

    def _build_researcher_prompt(self, task: str) -> str:
        """Build a strict prompt for the Web Research Agent persona."""
        from datetime import datetime
        import time as _time
        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        tz = _time.strftime("%Z") or "UTC"

        return f"""# Web Research & Troubleshooting Agent

## Current Time
{now} ({tz})

You are a highly specialized Web Research Agent spawned by the main Swarm to analyze a critical roadblock, error, or undocumented tool behavior.
Your SOLE purpose is to diagnose the failure, read the documentation, search the web, and formulate a concrete Resolution Plan so the primary task can resume.

## Directives
1. **Analyze the Error Context**: Read the provided task description which contains the error details.
2. **Search the Web**: Use `web_search` and `read_url_content` to find StackOverflow solutions, GitHub issues, or official API documentation matching the error or the tool.
3. **Formulate a Resolution**: Do not just say "I found the docs." Write a structured, step-by-step resolution plan on exactly what the main agent needs to do differently to fix the issue.
4. **Be Exhaustive**: If the first search result is unhelpful, keep digging.

## Workspace
Your workspace is at: {self.workspace}

Remember: Your output will be read by the Main Agent to attempt auto-recovery. Provide actionable, technically dense solutions!"""
    
    def get_running_count(self) -> int:
        """Return the number of currently running subagents."""
        return len(self._running_tasks)

    def get_active_subagents(self) -> dict[str, str]:
        """Return a dictionary of {task_id: task_description} for all running subagents."""
        active = {}
        for task_id in self._running_tasks:
            # We don't track the label explicitly in self._running_tasks, just the task object
            # For a proper dashboard, let's just use the task_id as the key for now. 
            # Subagent logging keeps track of the labels, but we can return the IDs.
            active[task_id] = "Running Background Task" 
        return active
