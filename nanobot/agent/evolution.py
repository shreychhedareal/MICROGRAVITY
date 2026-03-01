"""Capability Evolution Agent — the Swarm's self-improvement engine.

Logs tool limitations, agent bottlenecks, user complaints, and novel discoveries.
Analyzes patterns across logged issues and proposes systemic improvements.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Any
from loguru import logger


class EvolutionAgent:
    """
    Dedicated analytical agent for tracking and evolving Swarm capabilities.
    Operates on EVOLUTION_LEDGER.json as its persistent knowledge base.
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.ledger_path = workspace / "memory" / "EVOLUTION_LEDGER.json"

    def _load_ledger(self) -> list[dict[str, Any]]:
        if not self.ledger_path.exists():
            return []
        try:
            return json.loads(self.ledger_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_ledger(self, data: list[dict[str, Any]]):
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _next_id(self, data: list) -> str:
        return f"EVL-{len(data) + 1:03d}"

    def log_limitation(
        self,
        source_agent: str,
        description: str,
        impact: str = "medium",
        proposed_fix: str = "",
    ) -> dict[str, Any]:
        """Record a tool limitation or agent bottleneck."""
        data = self._load_ledger()
        entry = {
            "id": self._next_id(data),
            "timestamp": datetime.now().isoformat(),
            "category": "tool_limitation",
            "source_agent": source_agent,
            "description": description,
            "impact": impact,
            "proposed_fix": proposed_fix,
            "status": "open",
            "resolution_notes": "",
        }
        data.append(entry)
        self._save_ledger(data)
        logger.info(f"Evolution Agent logged limitation: {entry['id']} — {description[:80]}")
        return entry

    def log_user_feedback(
        self,
        description: str,
        impact: str = "medium",
        proposed_fix: str = "",
    ) -> dict[str, Any]:
        """Record a user complaint or suggestion for compliance tracking."""
        data = self._load_ledger()
        entry = {
            "id": self._next_id(data),
            "timestamp": datetime.now().isoformat(),
            "category": "user_complaint",
            "source_agent": "human_in_the_loop",
            "description": description,
            "impact": impact,
            "proposed_fix": proposed_fix,
            "status": "open",
            "resolution_notes": "",
        }
        data.append(entry)
        self._save_ledger(data)
        logger.info(f"Evolution Agent logged user feedback: {entry['id']} — {description[:80]}")
        return entry

    def log_novel_discovery(
        self,
        source_agent: str,
        description: str,
        proposed_fix: str = "",
    ) -> dict[str, Any]:
        """Record a novel or unique mode of use discovered via introspection."""
        data = self._load_ledger()
        entry = {
            "id": self._next_id(data),
            "timestamp": datetime.now().isoformat(),
            "category": "novel_discovery",
            "source_agent": source_agent,
            "description": description,
            "impact": "medium",
            "proposed_fix": proposed_fix,
            "status": "open",
            "resolution_notes": "",
        }
        data.append(entry)
        self._save_ledger(data)
        logger.info(f"Evolution Agent logged novel discovery: {entry['id']}")
        return entry

    def analyze_patterns(self) -> str:
        """Read the ledger, group recurring issues, and generate a diagnostic report."""
        data = self._load_ledger()
        if not data:
            return "Evolution Ledger is empty. No patterns to analyze."

        open_issues = [e for e in data if e.get("status") == "open"]
        by_category = {}
        by_source = {}
        critical_count = 0

        for entry in open_issues:
            cat = entry.get("category", "unknown")
            src = entry.get("source_agent", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1
            by_source[src] = by_source.get(src, 0) + 1
            if entry.get("impact") == "critical":
                critical_count += 1

        report_lines = [
            "=== EVOLUTION PATTERN ANALYSIS ===",
            f"Total open issues: {len(open_issues)}",
            f"Critical issues: {critical_count}",
            "",
            "--- By Category ---",
        ]
        for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
            report_lines.append(f"  {cat}: {count}")

        report_lines.append("")
        report_lines.append("--- By Source Agent ---")
        for src, count in sorted(by_source.items(), key=lambda x: -x[1]):
            report_lines.append(f"  {src}: {count}")

        # Highlight recurring bottlenecks
        report_lines.append("")
        report_lines.append("--- Top Bottlenecks ---")
        for entry in open_issues:
            if entry.get("impact") in ("high", "critical"):
                report_lines.append(f"  [{entry['id']}] {entry['description'][:100]}")
                if entry.get("proposed_fix"):
                    report_lines.append(f"    → Proposed: {entry['proposed_fix'][:100]}")

        return "\n".join(report_lines)

    def get_open_issues(self, category: str | None = None) -> list[dict[str, Any]]:
        """Retrieve open issues, optionally filtered by category."""
        data = self._load_ledger()
        open_items = [e for e in data if e.get("status") == "open"]
        if category:
            open_items = [e for e in open_items if e.get("category") == category]
        return open_items

    def resolve_issue(self, issue_id: str, resolution_notes: str) -> str:
        """Mark an issue as resolved."""
        data = self._load_ledger()
        for entry in data:
            if entry.get("id") == issue_id:
                entry["status"] = "resolved"
                entry["resolution_notes"] = resolution_notes
                self._save_ledger(data)
                return f"Issue {issue_id} marked as resolved."
        return f"Issue {issue_id} not found."
