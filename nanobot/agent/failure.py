import json
import logging
from pathlib import Path
from typing import Any, TYPE_CHECKING
import textwrap

from nanobot.bus.events import OutboundMessage
from nanobot.agent.evolution import EvolutionAgent

if TYPE_CHECKING:
    from nanobot.providers.base import LLMProvider
    from nanobot.bus.queue import MessageBus
    from nanobot.agent.subagent import SubagentManager

logger = logging.getLogger("nanobot.failure")

class FailureHandler:
    """
    Intelligent Triage system for handling Agent and Subagent crashes.
    Analyzes the stacktrace in the context of the active swarm dashboard and implementation tree.
    """
    
    def __init__(self, provider: "LLMProvider", bus: "MessageBus", model: str, workspace: Path | None = None):
        self.provider = provider
        self.bus = bus
        self.model = model
        self.evolution = EvolutionAgent(workspace) if workspace else None
        
    async def analyze_and_recover(
        self, 
        error_context: str, 
        swarm_status: str, 
        task_tree: str,
        channel: str,
        chat_id: str,
        subagents: "SubagentManager" = None
    ) -> None:
        """
        Analyze a failure, determine severity, and optionally trigger a recovery subagent 
        or notify the user.
        """
        
        prompt = textwrap.dedent(f"""
            An agent in the swarm has encountered a critical failure.
            
            [ERROR CONTEXT]
            {error_context}
            
            [CURRENT SWARM DASHBOARD]
            {swarm_status}
            
            [ACTIVE IMPLEMENTATION TREE / TO-DO LIST]
            {task_tree}
            
            Analyze this failure. If it is a simple missing dependency, file permission, or syntax error, 
            it might be Auto-Recoverable by spawning a diagnostic subagent to fix the environment or code.
            If it represents a fundamental architecture block or requires user credentials/decisions, it is NOT auto-recoverable.
            
            Output your analysis strictly in this structured JSON format:
            {{
                "severity": "Low|Medium|High|Critical",
                "impact": "Description of how this affects the Swarm Dashboard and Implementation Tree.",
                "solutions": ["List", "of", "exact", "steps", "to", "fix", "it"],
                "auto_recoverable": true/false,
                "user_notification": "A concise, polite message explaining the failure and impact to the user. (Leave empty if auto-recoverable silently)."
            }}
        """)
        
        try:
            # We use a JSON enforce prompt if the provider supports it, otherwise raw text parsing
            response = await self.provider.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse the triage
            triage_text = response.content.strip()
            if triage_text.startswith("```json"):
                triage_text = triage_text[7:-3]
            triage_data = json.loads(triage_text)
            
            severity = triage_data.get("severity", "High")
            impact = triage_data.get("impact", "Unknown impact")
            auto_recover = triage_data.get("auto_recoverable", False)
            notification = triage_data.get("user_notification", "")
            
            logger.info(f"Triage complete: Severity={severity}, Auto-Recover={auto_recover}")
            
            # Auto-log to Evolution Ledger
            if self.evolution:
                self.evolution.log_limitation(
                    source_agent="failure_handler",
                    description=f"Agent crash: {error_context[:200]}",
                    impact="critical" if severity == "Critical" else "high",
                    proposed_fix="; ".join(triage_data.get("solutions", [])),
                )
            
            # Announce triage to user if it's explicitly required or not auto-recoverable
            if notification or not auto_recover:
                triage_report = textwrap.dedent(f"""
                    ⚠️ **Swarm Triage Alert: {severity} Severity** ⚠️
                    {notification if notification else "The agent encountered an error it cannot automatically resolve."}
                    
                    **Impact Analytics:**
                    {impact}
                    
                    **Proposed Solutions:**
                    """ + "\n".join(f"- {sol}" for sol in triage_data.get("solutions", [])))
                
                await self.bus.publish_outbound(OutboundMessage(
                    channel=channel,
                    chat_id=chat_id,
                    content=triage_report
                ))
            
            # Attempt auto-recovery
            if auto_recover and subagents and triage_data.get("solutions"):
                recovery_task = (
                    "DIAGNOSTIC RECOVERY MISSION:\n"
                    "The swarm encountered an error. Execute these solutions immediately to repair the environment/system:\n" +
                    "\n".join(f"{i+1}. {sol}" for i, sol in enumerate(triage_data["solutions"]))
                )
                
                await self.bus.publish_outbound(OutboundMessage(
                    channel=channel,
                    chat_id=chat_id,
                    content="🔧 *Auto-Recovery initiated: Spawning a diagnostic subagent to patch the system.*"
                ))
                
                await subagents.spawn(
                    task=recovery_task,
                    label="Auto-Recovery Diagnostic",
                    origin_channel=channel,
                    origin_chat_id=chat_id
                )
                
        except Exception as triage_error:
            # Fallback if the LLM crashes during triage
            logger.error(f"FailureHandler triage crashed: {triage_error}")
            await self.bus.publish_outbound(OutboundMessage(
                channel=channel,
                chat_id=chat_id,
                content=f"Critical Error: {error_context[:200]}... \n(Triage system also failed to analyze this)."
            ))

    async def analyze_tool_error(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        tool_result: str,
        swarm_status: str,
        task_tree: str,
        channel: str,
        chat_id: str,
        subagents: "SubagentManager" = None
    ) -> None:
        """
        Analyze a tool failure to determine if it disrupts a larger objective.
        If it is a blocking failure, notify the user.
        """
        
        prompt = textwrap.dedent(f"""
            An agent tool execution just failed. We need to determine if this failure 
            blocks or disrupts a larger milestone/objective, requiring human notification.
            
            [TOOL NAME]
            {tool_name}
            
            [TOOL ARGUMENTS]
            {json.dumps(tool_args)}
            
            [TOOL ERROR OUTPUT]
            {tool_result}
            
            [CURRENT SWARM DASHBOARD]
            {swarm_status}
            
            [ACTIVE IMPLEMENTATION TREE / TO-DO LIST]
            {task_tree}
            
            Analyze this tool failure. Is it just a minor syntax error the agent can quickly retry and fix on its own? 
            Or does this fundamentally block a major objective (e.g. missing API key, service down, missing credential, 
            or complete inability to complete the milestone listed in the To-Do list)?
            
            Crucially, if the error is extremely strange, implies a missing dependency, or looks like a library bug or API change, we need to dispatch a Web Research Agent to look it up online and find a solution.
            
            Output your analysis strictly in this structured JSON format:
            {{
                "is_blocking": true/false,
                "needs_research": true/false,
                "severity": "Low|Medium|High|Critical",
                "notification": "If it is blocking or requires research, write a concise, polite message alerting the user that their objective is paused while we investigate the failure. If not blocking, leave empty."
            }}
        """)
        
        try:
            response = await self.provider.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            
            triage_text = response.content.strip() if response.content else ""
            if triage_text.startswith("```json"):
                triage_text = triage_text[7:-3].strip()
            elif triage_text.startswith("```"):
                triage_text = triage_text[3:-3].strip()
                
            try:
                triage_data = json.loads(triage_text)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse triage JSON: {triage_text}")
                triage_data = {}
            
            is_blocking = triage_data.get("is_blocking", False)
            needs_research = triage_data.get("needs_research", False)
            severity = triage_data.get("severity", "Low")
            notification = triage_data.get("notification", "")
            
            logger.info(f"Tool Disruption Triage: {tool_name} -> Blocking={is_blocking}, Research={needs_research}, Severity={severity}")
            
            # Auto-log tool failures to Evolution Ledger
            if self.evolution and is_blocking:
                auth_keywords = ["credential", "login", "password", "auth", "401", "403", "forbidden"]
                is_auth_failure = any(kw in tool_result.lower() for kw in auth_keywords)
                self.evolution.log_limitation(
                    source_agent=tool_name,
                    description=f"{'Auth failure' if is_auth_failure else 'Tool failure'}: {tool_result[:200]}",
                    impact="critical" if is_auth_failure else severity.lower(),
                    proposed_fix=notification[:200] if notification else "",
                )
            
            if (is_blocking or needs_research) and notification:
                alert = textwrap.dedent(f"""
                    ⛔ **Task Disruption Alert ({severity})** ⛔
                    A tool failure has interrupted the active objective:
                    
                    {notification}
                    
                    *(Tool `{tool_name}` error trapped).*
                """)
                
                await self.bus.publish_outbound(OutboundMessage(
                    channel=channel,
                    chat_id=chat_id,
                    content=alert.strip()
                ))
            
            if needs_research and subagents:
                research_task = (
                    "DEEP RESEARCH MISSION:\n"
                    f"The main agent failed while executing `{tool_name}`.\n"
                    f"Arguments attempted:\n{json.dumps(tool_args)}\n\n"
                    f"Error Output:\n{tool_result}\n\n"
                    "Please search the web, read API docs or Github issues, and formulate a concrete step-by-step resolution plan so the main agent can retry this successfully later."
                )
                
                await self.bus.publish_outbound(OutboundMessage(
                    channel=channel,
                    chat_id=chat_id,
                    content="🔍 *Auto-Recovery initiated: Spawning a specialized Web Research Agent to investigate the root cause of this failure...*"
                ))
                
                await subagents.spawn(
                    task=research_task,
                    label="Failure Diagnostics Research",
                    origin_channel=channel,
                    origin_chat_id=chat_id,
                    persona="researcher"
                )
                
        except Exception as triage_error:
            logger.error(f"FailureHandler tool triage crashed: {triage_error}")
