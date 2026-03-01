"""Agent loop: the core processing engine."""

from __future__ import annotations

import asyncio
import json
import re
from contextlib import AsyncExitStack
from pathlib import Path
from typing import TYPE_CHECKING, Awaitable, Callable

from loguru import logger

from nanobot.agent.context import ContextBuilder
from nanobot.agent.memory import MemoryStore
from nanobot.agent.subagent import SubagentManager
from nanobot.agent.tools.cron import CronTool
from nanobot.agent.tools.filesystem import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from nanobot.agent.tools.message import MessageTool
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.shell import ExecTool
from nanobot.agent.tools.spawn import SpawnTool
from nanobot.agent.tools.web import WebFetchTool, WebSearchTool
from nanobot.agent.tools.browser import BrowserTool
from nanobot.agent.tools.swarm import SwarmStatusTool
from nanobot.agent.tools.tasks import TaskTrackerTool
from nanobot.agent.tools.profile import UserProfileTool
from nanobot.agent.tools.memory_tools import SearchHistoryTool, UpdateMemoryTool, ReadMemoryTool, SemanticSearchTool
from nanobot.agent.tools.capability import AnalyzeCapabilityExpansionTool
from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMProvider
from nanobot.session.manager import Session, SessionManager
from nanobot.agent.introspection import IntrospectionManager
from nanobot.agent.failure import FailureHandler

if TYPE_CHECKING:
    from nanobot.config.schema import ExecToolConfig
    from nanobot.cron.service import CronService


class AgentLoop:
    """
    The agent loop is the core processing engine.

    It:
    1. Receives messages from the bus
    2. Builds context with history, memory, skills
    3. Calls the LLM
    4. Executes tool calls
    5. Sends responses back
    """

    def __init__(
        self,
        bus: MessageBus,
        provider: LLMProvider,
        workspace: Path,
        model: str | None = None,
        max_iterations: int = 20,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        memory_window: int = 50,
        brave_api_key: str | None = None,
        exec_config: ExecToolConfig | None = None,
        cron_service: CronService | None = None,
        restrict_to_workspace: bool = False,
        session_manager: SessionManager | None = None,
        mcp_servers: dict | None = None,
    ):
        from nanobot.config.schema import ExecToolConfig
        self.bus = bus
        self.provider = provider
        self.workspace = workspace
        self.model = model or provider.get_default_model()
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.memory_window = memory_window
        self.brave_api_key = brave_api_key
        self.exec_config = exec_config or ExecToolConfig()
        self.cron_service = cron_service
        self.restrict_to_workspace = restrict_to_workspace

        self.context = ContextBuilder(workspace)
        self.sessions = session_manager or SessionManager(workspace)
        self.tools = ToolRegistry()
        self.subagents = SubagentManager(
            provider=provider,
            workspace=workspace,
            bus=bus,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            brave_api_key=brave_api_key,
            exec_config=self.exec_config,
            restrict_to_workspace=restrict_to_workspace,
        )

        self._running = False
        self._mcp_servers = mcp_servers or {}
        self._mcp_stack: AsyncExitStack | None = None
        self._mcp_connected = False
        self._mcp_connecting = False
        self._consolidating: set[str] = set()  # Session keys with consolidation in progress
        self._active_tasks: dict[str, asyncio.Task] = {}  # Track running tasks per session
        self._pending_interrupt: dict[str, dict] = {} # Track pending interruptions
        self.introspection = IntrospectionManager(provider=self.provider, model=self.model, workspace=self.workspace)
        self.failure_handler = FailureHandler(provider=self.provider, bus=self.bus, model=self.model, workspace=self.workspace)
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register the default set of tools."""
        allowed_dir = self.workspace if self.restrict_to_workspace else None
        for cls in (ReadFileTool, WriteFileTool, EditFileTool, ListDirTool):
            self.tools.register(cls(workspace=self.workspace, allowed_dir=allowed_dir))
        self.tools.register(ExecTool(
            working_dir=str(self.workspace),
            timeout=self.exec_config.timeout,
            restrict_to_workspace=self.restrict_to_workspace,
        ))
        self.tools.register(WebSearchTool(api_key=self.brave_api_key))
        self.tools.register(WebFetchTool())
        self.tools.register(BrowserTool())
        from nanobot.agent.tools.environment import ReadEnvVarTool, SetEnvVarTool
        self.tools.register(ReadEnvVarTool())
        self.tools.register(SetEnvVarTool())
        from nanobot.agent.tools.path_memory import BookmarkPathTool, RecallPathsTool
        from nanobot.agent.tools.code_analyzer import OutlineCodeTool, AnnotateCodeTool
        from nanobot.agent.tools.diagnostics import ReadLogsTool
        self.tools.register(BookmarkPathTool(workspace=self.workspace))
        self.tools.register(RecallPathsTool(workspace=self.workspace))
        self.tools.register(OutlineCodeTool())
        self.tools.register(AnnotateCodeTool())
        self.tools.register(ReadLogsTool(workspace=self.workspace))
        self.tools.register(MessageTool(send_callback=self.bus.publish_outbound))
        self.tools.register(SpawnTool(manager=self.subagents))
        self.tools.register(SwarmStatusTool(manager=self.subagents, agent_loop=self))
        self.tools.register(TaskTrackerTool(workspace_path=self.workspace))
        self.tools.register(UserProfileTool(workspace_path=self.workspace))
        self.tools.register(SearchHistoryTool(workspace=self.workspace))
        self.tools.register(UpdateMemoryTool(workspace=self.workspace))
        self.tools.register(ReadMemoryTool(workspace=self.workspace))
        self.tools.register(SemanticSearchTool(workspace=self.workspace))
        self.tools.register(AnalyzeCapabilityExpansionTool(workspace=self.workspace))
        
        from nanobot.agent.tools.credentials import SearchCredentialTool, StoreCredentialTool, InvalidateCredentialTool
        from nanobot.agent.tools.evolution import LogIssueTool, LogUserFeedbackTool, ViewEvolutionReportTool
        self.tools.register(SearchCredentialTool(workspace=self.workspace))
        self.tools.register(StoreCredentialTool(workspace=self.workspace))
        self.tools.register(InvalidateCredentialTool(workspace=self.workspace))
        self.tools.register(LogIssueTool(workspace=self.workspace))
        self.tools.register(LogUserFeedbackTool(workspace=self.workspace))
        self.tools.register(ViewEvolutionReportTool(workspace=self.workspace))
        
        if self.cron_service:
            self.tools.register(CronTool(self.cron_service))

    async def _connect_mcp(self) -> None:
        """Connect to configured MCP servers (one-time, lazy)."""
        if self._mcp_connected or self._mcp_connecting or not self._mcp_servers:
            return
        self._mcp_connecting = True
        from nanobot.agent.tools.mcp import connect_mcp_servers
        try:
            self._mcp_stack = AsyncExitStack()
            await self._mcp_stack.__aenter__()
            await connect_mcp_servers(self._mcp_servers, self.tools, self._mcp_stack)
            self._mcp_connected = True
        except Exception as e:
            logger.error("Failed to connect MCP servers (will retry next message): {}", e)
            if self._mcp_stack:
                try:
                    await self._mcp_stack.aclose()
                except Exception:
                    pass
                self._mcp_stack = None
        finally:
            self._mcp_connecting = False

    def _set_tool_context(self, channel: str, chat_id: str, message_id: str | None = None) -> None:
        """Update context for all tools that need routing info."""
        if message_tool := self.tools.get("message"):
            if isinstance(message_tool, MessageTool):
                message_tool.set_context(channel, chat_id, message_id)

        if spawn_tool := self.tools.get("spawn"):
            if isinstance(spawn_tool, SpawnTool):
                spawn_tool.set_context(channel, chat_id)

        if cron_tool := self.tools.get("cron"):
            if isinstance(cron_tool, CronTool):
                cron_tool.set_context(channel, chat_id)

    @staticmethod
    def _strip_think(text: str | None) -> str | None:
        """Remove <think>…</think> blocks that some models embed in content."""
        if not text:
            return None
        return re.sub(r"<think>[\s\S]*?</think>", "", text).strip() or None

    @staticmethod
    def _tool_hint(tool_calls: list) -> str:
        """Format tool calls as concise hint, e.g. 'web_search("query")'."""
        def _fmt(tc):
            val = next(iter(tc.arguments.values()), None) if tc.arguments else None
            if not isinstance(val, str):
                return tc.name
            return f'{tc.name}("{val[:40]}…")' if len(val) > 40 else f'{tc.name}("{val}")'
        return ", ".join(_fmt(tc) for tc in tool_calls)

    async def _run_agent_loop(
        self,
        initial_messages: list[dict],
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> tuple[str | None, list[str]]:
        """Run the agent iteration loop. Returns (final_content, tools_used)."""
        messages = initial_messages
        iteration = 0
        final_content = None
        tools_used: list[str] = []

        while iteration < self.max_iterations:
            iteration += 1

            response = await self.provider.chat(
                messages=messages,
                tools=self.tools.get_definitions(),
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            if response.has_tool_calls:
                if on_progress:
                    clean = self._strip_think(response.content)
                    if clean:
                        await on_progress(clean)
                    await on_progress(self._tool_hint(response.tool_calls))

                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False)
                        }
                    }
                    for tc in response.tool_calls
                ]
                messages = self.context.add_assistant_message(
                    messages, response.content, tool_call_dicts,
                    reasoning_content=response.reasoning_content,
                )

                for tool_call in response.tool_calls:
                    tools_used.append(tool_call.name)
                    args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
                    logger.info("Tool call: {}({})", tool_call.name, args_str[:200])
                    
                    if tool_call.name == "message":
                        content_to_send = tool_call.arguments.get("content", "")
                        if on_progress:
                            await on_progress("⏳ Introspecting outbound chat message...")
                        
                        is_obj_approved, msg_feedback = await self.introspection.evaluate(
                            messages=messages,
                            draft_content=content_to_send,
                            tools_used=tools_used,
                            publish_progress=on_progress
                        )
                        if not is_obj_approved:
                            result = (
                                f"[SYSTEM/SUPERVISOR REJECTION]\n"
                                f"Message blocked. Your draft was rejected:\n"
                                f"{msg_feedback}\n\n"
                                f"RE-PLANNING REQUIRED: Re-process data or use tools to fulfill the actual objective."
                            )
                            logger.warning(f"Introspection blocked message. Feedback: {msg_feedback}")
                        else:
                            result = await self.tools.execute(tool_call.name, tool_call.arguments)
                    else:
                        result = await self.tools.execute(tool_call.name, tool_call.arguments)
                    
                    # --- DYNAMIC MEMORY INTERCEPTION ---
                    # If any tool (especially UI/UX Planner) explicitly tells us it discovered a stable
                    # environment landmark, we write it immediately to persistent machine memory 
                    # before the LLM even sees it, guaranteeing zero-loss spatial awareness.
                    if isinstance(result, str) and "[SYSTEM_MEMORY_TRIGGER]" in result:
                        try:
                            logger.info("SYSTEM_MEMORY_TRIGGER detected. Auto-mapping coordinate to UI_ATLAS.")
                            store = MemoryStore(self.workspace)
                            
                            # Extremely simple regex/split parser designed for the strict ui_ux.py output format
                            trigger_blocks = result.split("[SYSTEM_MEMORY_TRIGGER]")
                            for block in trigger_blocks[1:]:
                                if "Discovered stable landmark" in block:
                                    parts = block.split("stable landmark '")[1].split("'")
                                    name = parts[0]
                                    coords = parts[1].split("(")[1].split(")")[0]
                                    x, y = coords.split(", ")
                                    
                                    content = store.read_text("UI_ATLAS.md")
                                    if content:
                                        row = f"- {name} | Launch App | Coordinate ({x}, {y})"
                                        if name not in content:
                                            # Write to LMDB natively
                                            content = content.replace("### Desktop Elements", f"### Desktop Elements\n{row}")
                                            store.write_text("UI_ATLAS.md", content)
                                            
                                            # We append a success confirmation directly into the tool result 
                                            # so the LLM knows it was permanently saved.
                                            result += f"\n[Framework Note]: Landmark '{name}' auto-saved to UI_ATLAS.md."
                        except Exception as e:
                            logger.error(f"Failed to parse or write memory trigger: {e}")
                    # -----------------------------------
                    
                    # Intercept potential tool failures for disruption analysis
                    if isinstance(result, str):
                        is_error = False
                        result_lower = result.lower()
                        if result_lower.startswith("error:") or result_lower.startswith("exception:"):
                            is_error = True
                        elif "exit code: " in result_lower and "exit code: 0" not in result_lower:
                            is_error = True
                        elif "status" in result_lower and "error" in result_lower:
                            # Catch JSON errors like BrowserTool returns
                            try:
                                parsed = json.loads(result)
                                if isinstance(parsed, dict) and parsed.get("status") == "error":
                                    is_error = True
                            except Exception: pass
                            
                        if is_error:
                            logger.info(f"Detected tool execution error in {tool_call.name}, dispatching to Triage")
                            
                            # Gather context
                            swarm_status = "Unknown (Failed to gather status)"
                            try:
                                from nanobot.agent.tools.swarm import SwarmStatusTool
                                swarm_tool = SwarmStatusTool(self.subagents, self)
                                swarm_status = await swarm_tool.execute()
                            except Exception: pass
                            
                            task_tree = "Unknown (Failed to read tasks)"
                            try:
                                from nanobot.agent.tools.tasks import TaskTrackerTool
                                task_tool = TaskTrackerTool(self.workspace)
                                task_tree = await task_tool.execute("read")
                            except Exception: pass
                            
                            # Dispatch asynchronously
                            asyncio.create_task(
                                self.failure_handler.analyze_tool_error(
                                    tool_name=tool_call.name,
                                    tool_args=tool_call.arguments,
                                    tool_result=result,
                                    swarm_status=swarm_status,
                                    task_tree=task_tree,
                                    channel=msg.channel if 'msg' in locals() else "cli",
                                    chat_id=msg.chat_id if 'msg' in locals() else "direct",
                                    subagents=self.subagents
                                )
                            )
                            
                    messages = self.context.add_tool_result(
                        messages, tool_call.id, tool_call.name, result
                    )
            else:
                final_content = self._strip_think(response.content)
                
                # Intercept the draft response using the Introspection Manager
                if on_progress:
                    await on_progress("⏳ Analyzing draft response for optimal execution...")
                    
                is_approved, corrective_feedback = await self.introspection.evaluate(
                    messages=messages,
                    draft_content=final_content or "",
                    tools_used=tools_used,
                    publish_progress=on_progress
                )
                
                if not is_approved:
                    # Inject the supervisor's critique as a tool-like intervention 
                    # from the 'user' or 'system' perspective to force correction.
                    critique_msg = (
                        f"[SYSTEM/SUPERVISOR REJECTION]\n"
                        f"Your response was rejected for the following reason:\n"
                        f"{corrective_feedback}\n\n"
                        f"RE-PLANNING REQUIRED: Do not merely apologize or tweak the text. You must re-process the data, write scripts, or use tools to fulfill the actual objective."
                    )
                    
                    messages = self.context.add_assistant_message(
                        messages, final_content, [], reasoning_content=response.reasoning_content
                    )
                    messages.append({"role": "user", "content": critique_msg})
                    logger.warning(f"Introspection rejection triggered retry loop. Feedback: {corrective_feedback}")
                    
                    # Yield to event loop to allow pending cancellations to be processed
                    await asyncio.sleep(0)
                    
                    # We do not break here; instead, we loop again to allow the agent to correct itself.
                    final_content = None 
                    continue
                    
                break
                
            # Check for interruptions between tool calls
            # Assuming session_key is passed via a property or accessible context:
            # We will handle task cancellation externally, so if this Task is cancelled
            # asyncio.CancelledError will be raised automatically when it hits await boundaries.

        return final_content, tools_used

    async def run(self) -> None:
        """Run the agent loop, processing messages from the bus."""
        self._running = True
        await self._connect_mcp()
        logger.info("Agent loop started")

        while self._running:
            try:
                msg = await asyncio.wait_for(
                    self.bus.consume_inbound(),
                    timeout=1.0
                )
                
                # Handle concurrently
                session_key = msg.session_key if not msg.channel == "system" else f"{msg.channel}:{msg.chat_id}"
                
                # Check for interruption logic
                if session_key in self._active_tasks and not self._active_tasks[session_key].done():
                    # There is an active task running for this session.
                    if msg.content.lower().strip() in ["yes", "y"]:
                        if session_key in self._pending_interrupt:
                            # User agreed to interrupt
                            logger.info(f"Interrupting active task for session {session_key}")
                            self._active_tasks[session_key].cancel()
                            
                            # Start the new buffered task
                            buffered_msg = self._pending_interrupt.pop(session_key)
                            task = asyncio.create_task(self._process_and_publish(buffered_msg))
                            self._active_tasks[session_key] = task
                        else:
                            await self.bus.publish_outbound(OutboundMessage(
                                channel=msg.channel, chat_id=msg.chat_id, 
                                content="No pending task to interrupt."
                            ))
                        continue
                        
                    elif msg.content.lower().strip() in ["no", "n"] and session_key in self._pending_interrupt:
                        # User declined interruption
                        self._pending_interrupt.pop(session_key)
                        await self.bus.publish_outbound(OutboundMessage(
                            channel=msg.channel, chat_id=msg.chat_id, 
                            content="Understood. Resuming previous task."
                        ))
                        continue
                        
                    elif session_key not in self._pending_interrupt:
                        # Ask for interruption confirmation
                        self._pending_interrupt[session_key] = msg
                        await self.bus.publish_outbound(OutboundMessage(
                            channel=msg.channel, chat_id=msg.chat_id, 
                            content="I am currently working on your previous request. Do you want me to stop that task and start this new one? (Yes/No)"
                        ))
                        continue
                    else:
                        # Waiting for yes/no, overwrite buffer
                        self._pending_interrupt[session_key] = msg
                        await self.bus.publish_outbound(OutboundMessage(
                            channel=msg.channel, chat_id=msg.chat_id, 
                            content="Please answer 'Yes' or 'No' to interrupt the ongoing task."
                        ))
                        continue

                # No active task, run normally
                task = asyncio.create_task(self._process_and_publish(msg))
                self._active_tasks[session_key] = task
                
            except asyncio.TimeoutError:
                continue

    async def _process_and_publish(self, msg: InboundMessage) -> None:
        """Wrapper to safely execute _process_message inside a Task."""
        try:
            response = await self._process_message(msg)
            if response is not None:
                await self.bus.publish_outbound(response)
            elif msg.channel == "cli":
                await self.bus.publish_outbound(OutboundMessage(
                    channel=msg.channel, chat_id=msg.chat_id, content="", metadata=msg.metadata or {},
                ))
        except asyncio.CancelledError:
            logger.info("Task cancelled mid-execution: {}", msg.content)
            await self.bus.publish_outbound(OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content="[Task automatically cancelled.]"
            ))
        except Exception as e:
            logger.error("Error processing message: {}", e)
            
            import traceback
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            
            # Use the new SwarmStatusTool and TaskTrackerTool to gather context for the failure
            swarm_status = "Unknown (Failed to gather status)"
            try:
                from nanobot.agent.tools.swarm import SwarmStatusTool
                swarm_tool = SwarmStatusTool(self.subagents, self)
                swarm_status = await swarm_tool.execute()
            except Exception: pass
            
            task_tree = "Unknown (Failed to read tasks)"
            try:
                from nanobot.agent.tools.tasks import TaskTrackerTool
                task_tool = TaskTrackerTool(self.workspace)
                task_tree = await task_tool.execute("read")
            except Exception: pass
            
            # Send to Triage System instead of dumb dump
            asyncio.create_task(
                self.failure_handler.analyze_and_recover(
                    error_context=error_msg,
                    swarm_status=swarm_status,
                    task_tree=task_tree,
                    channel=msg.channel,
                    chat_id=msg.chat_id,
                    subagents=self.subagents
                )
            )
            
        finally:
            if msg.session_key in self._active_tasks:
                if self._active_tasks[msg.session_key] == asyncio.current_task():
                    del self._active_tasks[msg.session_key]

    async def close_mcp(self) -> None:
        """Close MCP connections."""
        if self._mcp_stack:
            try:
                await self._mcp_stack.aclose()
            except (RuntimeError, BaseExceptionGroup):
                pass  # MCP SDK cancel scope cleanup is noisy but harmless
            self._mcp_stack = None

    def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
        logger.info("Agent loop stopping")

    async def _process_message(
        self,
        msg: InboundMessage,
        session_key: str | None = None,
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> OutboundMessage | None:
        """Process a single inbound message and return the response."""
        # System messages: parse origin from chat_id ("channel:chat_id")
        if msg.channel == "system":
            channel, chat_id = (msg.chat_id.split(":", 1) if ":" in msg.chat_id
                                else ("cli", msg.chat_id))
            logger.info("Processing system message from {}", msg.sender_id)
            key = f"{channel}:{chat_id}"
            session = self.sessions.get_or_create(key)
            self._set_tool_context(channel, chat_id, msg.metadata.get("message_id"))
            messages = self.context.build_messages(
                history=session.get_history(max_messages=self.memory_window),
                current_message=msg.content, channel=channel, chat_id=chat_id,
            )
            final_content, _ = await self._run_agent_loop(messages)
            session.add_message("user", f"[System: {msg.sender_id}] {msg.content}")
            session.add_message("assistant", final_content or "Background task completed.")
            self.sessions.save(session)
            return OutboundMessage(channel=channel, chat_id=chat_id,
                                  content=final_content or "Background task completed.")

        preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        logger.info("Processing message from {}:{}: {}", msg.channel, msg.sender_id, preview)

        key = session_key or msg.session_key
        session = self.sessions.get_or_create(key)

        # Slash commands
        cmd = msg.content.strip().lower()
        if cmd == "/new":
            messages_to_archive = session.messages.copy()
            session.clear()
            self.sessions.save(session)
            self.sessions.invalidate(session.key)

            async def _consolidate_and_cleanup():
                temp = Session(key=session.key)
                temp.messages = messages_to_archive
                await self._consolidate_memory(temp, archive_all=True)

            asyncio.create_task(_consolidate_and_cleanup())
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id,
                                  content="New session started. Memory consolidation in progress.")
        if cmd == "/help":
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id,
                                  content="🐈 nanobot commands:\n/new — Start a new conversation\n/help — Show available commands")

        if len(session.messages) > self.memory_window and session.key not in self._consolidating:
            self._consolidating.add(session.key)

            async def _consolidate_and_unlock():
                try:
                    await self._consolidate_memory(session)
                finally:
                    self._consolidating.discard(session.key)

            asyncio.create_task(_consolidate_and_unlock())

            

        self._set_tool_context(msg.channel, msg.chat_id, msg.metadata.get("message_id"))
        if message_tool := self.tools.get("message"):
            if isinstance(message_tool, MessageTool):
                message_tool.start_turn()

        initial_messages = self.context.build_messages(
            history=session.get_history(max_messages=self.memory_window),
            current_message=msg.content,
            media=msg.media if msg.media else None,
            channel=msg.channel, chat_id=msg.chat_id,
        )

        async def _bus_progress(content: str) -> None:
            meta = dict(msg.metadata or {})
            meta["_progress"] = True
            await self.bus.publish_outbound(OutboundMessage(
                channel=msg.channel, chat_id=msg.chat_id, content=content, metadata=meta,
            ))

        final_content, tools_used = await self._run_agent_loop(
            initial_messages, on_progress=on_progress or _bus_progress,
        )

        if final_content is None:
            final_content = "I've completed processing but have no response to give."

        preview = final_content[:120] + "..." if len(final_content) > 120 else final_content
        logger.info("Response to {}:{}: {}", msg.channel, msg.sender_id, preview)

        session.add_message("user", msg.content)
        session.add_message("assistant", final_content,
                            tools_used=tools_used if tools_used else None)
        self.sessions.save(session)

        if message_tool := self.tools.get("message"):
            if isinstance(message_tool, MessageTool) and message_tool._sent_in_turn:
                return None

        return OutboundMessage(
            channel=msg.channel, chat_id=msg.chat_id, content=final_content,
            metadata=msg.metadata or {},
        )

    async def _consolidate_memory(self, session, archive_all: bool = False) -> None:
        """Delegate to MemoryStore.consolidate()."""
        await MemoryStore(self.workspace).consolidate(
            session, self.provider, self.model,
            archive_all=archive_all, memory_window=self.memory_window,
        )

    async def process_direct(
        self,
        content: str,
        session_key: str = "cli:direct",
        channel: str = "cli",
        chat_id: str = "direct",
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        """Process a message directly (for CLI or cron usage)."""
        await self._connect_mcp()
        msg = InboundMessage(channel=channel, sender_id="user", chat_id=chat_id, content=content)
        response = await self._process_message(msg, session_key=session_key, on_progress=on_progress)
        return response.content if response else ""
