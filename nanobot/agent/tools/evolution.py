"""Tools for logging limitations, user feedback, and viewing the Evolution report."""

import json
from pathlib import Path
from typing import Any
from nanobot.agent.tools.base import Tool
from nanobot.agent.evolution import EvolutionAgent


class LogIssueTool(Tool):
    """Log a tool limitation, bottleneck, or agent shortcoming."""

    def __init__(self, workspace: Path):
        self.agent = EvolutionAgent(workspace)

    @property
    def name(self) -> str:
        return "log_issue"

    @property
    def description(self) -> str:
        return (
            "Log a tool limitation, bottleneck, or agent shortcoming encountered during execution. "
            "Use this whenever a tool fails, hits a constraint, or you discover a missing capability. "
            "Also use it to record novel/unique modes of use discovered via introspection."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source_agent": {
                    "type": "string",
                    "description": "Which agent or tool reported this (e.g. 'browser', 'subagent', 'credential_manager')."
                },
                "description": {
                    "type": "string",
                    "description": "Clear description of the limitation, bottleneck, or discovery."
                },
                "category": {
                    "type": "string",
                    "enum": ["tool_limitation", "agent_bottleneck", "novel_discovery"],
                    "description": "The type of issue being logged."
                },
                "impact": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Severity of the issue."
                },
                "proposed_fix": {
                    "type": "string",
                    "description": "Optional: your proposed solution or improvement."
                }
            },
            "required": ["source_agent", "description", "category", "impact"],
        }

    async def execute(self, source_agent: str, description: str, category: str, impact: str, proposed_fix: str = "", **kwargs: Any) -> str:
        if category == "novel_discovery":
            entry = self.agent.log_novel_discovery(source_agent, description, proposed_fix)
        else:
            entry = self.agent.log_limitation(source_agent, description, impact, proposed_fix)
        return f"✅ Logged to Evolution Ledger as [{entry['id']}]: {description[:80]}"


class LogUserFeedbackTool(Tool):
    """Record a user complaint or suggestion for compliance tracking."""

    def __init__(self, workspace: Path):
        self.agent = EvolutionAgent(workspace)

    @property
    def name(self) -> str:
        return "log_user_feedback"

    @property
    def description(self) -> str:
        return (
            "Record a user complaint, suggestion, or feature request for compliance tracking. "
            "Use this when the user expresses dissatisfaction, proposes an improvement, or requests "
            "a capability that doesn't exist yet. This triggers deeper research into the feasibility."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "The user's feedback, complaint, or feature request."
                },
                "impact": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "How important is this to the user?"
                },
                "proposed_fix": {
                    "type": "string",
                    "description": "Your initial assessment of how to address this feedback."
                }
            },
            "required": ["description", "impact"],
        }

    async def execute(self, description: str, impact: str, proposed_fix: str = "", **kwargs: Any) -> str:
        entry = self.agent.log_user_feedback(description, impact, proposed_fix)
        return f"📝 User feedback logged as [{entry['id']}]: {description[:80]}. Flagged for compliance research."


class ViewEvolutionReportTool(Tool):
    """Retrieve a diagnostic report of open issues and improvement proposals."""

    def __init__(self, workspace: Path):
        self.agent = EvolutionAgent(workspace)

    @property
    def name(self) -> str:
        return "view_evolution_report"

    @property
    def description(self) -> str:
        return (
            "Retrieve a summary of all open tool limitations, agent bottlenecks, user complaints, "
            "and improvement proposals from the Evolution Ledger. Use this to understand the "
            "Swarm's current shortcomings and plan upgrades."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "category_filter": {
                    "type": "string",
                    "enum": ["tool_limitation", "agent_bottleneck", "user_complaint", "novel_discovery", "all"],
                    "description": "Filter by category, or 'all' for everything."
                }
            },
            "required": [],
        }

    async def execute(self, category_filter: str = "all", **kwargs: Any) -> str:
        report = self.agent.analyze_patterns()
        if category_filter and category_filter != "all":
            issues = self.agent.get_open_issues(category=category_filter)
            if issues:
                filtered = "\n".join([f"[{e['id']}] {e['description'][:100]}" for e in issues])
                return f"{report}\n\n--- Filtered ({category_filter}) ---\n{filtered}"
        return report
