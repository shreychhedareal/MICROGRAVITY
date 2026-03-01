"""Adaptive Introspection Manager — dynamic, self-improving supervisor.

Upgrades the static rule-based supervisor into an adaptive system that:
1. PLANS which introspection checks are relevant for the current objective.
2. AUDITS whether those checks actually improved the output (track hit/miss).
3. UPDATES its own rules based on feedback loops and constraint violations.
4. COURSE-CORRECTS when deliverables diverge from the original objective.
"""

import json
import json_repair
import time
from pathlib import Path
from loguru import logger
from typing import Any, Tuple, Optional, Callable, Awaitable

from nanobot.providers.base import LLMProvider
from nanobot.bus.events import OutboundMessage


# ── Core Rule Library ──
# Each rule has an ID, description, relevance tags, and the check text.
INTROSPECTION_RULES = [
    {
        "id": "R1_NO_REFUSAL",
        "tags": ["capability", "tool_usage", "browser", "desktop"],
        "description": "Agent must not refuse tasks claiming it lacks capabilities.",
        "check": (
            "Did the agent refuse a task claiming it lacks capabilities "
            "(e.g., 'I cannot log in', 'I operate in a headless environment', 'I cannot see your screen')? "
            "If so, REJECT. If the agent complains about being 'headless', "
            "explicitly instruct it to use the `browser` tool."
        ),
    },
    {
        "id": "R2_PREMATURE_STOP",
        "tags": ["error_handling", "persistence", "retry"],
        "description": "Agent must not stop prematurely on recoverable errors.",
        "check": "Did the agent stop prematurely due to a recoverable error? If so, REJECT.",
    },
    {
        "id": "R3_CREDENTIAL_INVALIDATION",
        "tags": ["credential", "login", "auth"],
        "description": "Failed credentials must be invalidated before asking user.",
        "check": (
            "Did the agent attempt to login to a platform, but the credentials failed? "
            "If so, REJECT and forcefully instruct the agent to use the `invalidate_credential` tool "
            "to mark the broken credential in the vault before asking the user for new ones."
        ),
    },
    {
        "id": "R3b_CREDENTIAL_PREFETCH",
        "tags": ["credential", "login", "auth"],
        "description": "Agent must check vault before asking user for passwords.",
        "check": (
            "Did the agent ask the user for a password or login credentials WITHOUT first calling "
            "`search_credential`? If so, REJECT and instruct it to check the vault first."
        ),
    },
    {
        "id": "R4_SWARM_IDENTITY",
        "tags": ["memory", "discovery", "machine_env"],
        "description": "New discoveries must update Machine Knowledge Base.",
        "check": (
            "Did the agent discover a new app, file, Repo, or UI element but FAIL to trigger an "
            "update to the Machine Knowledge Base (MACHINE_ENV, REPO_CATALOG, UI_ATLAS)? "
            "If so, REJECT and instruct it to update its memory."
        ),
    },
    {
        "id": "R5_EXPERIENTIAL_LEARNING",
        "tags": ["learning", "novel_task", "documentation"],
        "description": "Novel complex tasks must be documented in Experience Ledger.",
        "check": (
            "If the agent successfully completed a novel complex/multi-step task, did it document "
            "the tool orchestration and constraints into `EXPERIENCE_LEDGER.md`? If not, REJECT."
        ),
    },
    {
        "id": "R6_EVOLUTION_LOG",
        "tags": ["evolution", "limitation", "feedback"],
        "description": "Tool limitations and user complaints must be logged.",
        "check": (
            "If the agent encountered a tool limitation, bottleneck, or the user explicitly complained "
            "about a missing feature, did the agent use `log_issue` or `log_user_feedback` to record it? "
            "If not, REJECT and instruct it to log the issue."
        ),
    },
    {
        "id": "R7_OBJECTIVE_ALIGNMENT",
        "tags": ["quality", "intent", "completion"],
        "description": "Response must optimally fulfill the user's core intent.",
        "check": (
            "Is the agent's response optimal and completely fulfilling the user's core intent? "
            "Does it deliver the actual requested output, not just a description of what it did? "
            "If the output is incomplete, vague, or tangential, REJECT."
        ),
    },
]


class IntrospectionManager:
    """
    Adaptive Introspection Supervisor that dynamically plans, audits,
    and course-corrects its review process based on the current objective.
    """

    def __init__(self, provider: LLMProvider, model: str, workspace: Path | None = None):
        self.provider = provider
        self.model = model
        self.workspace = workspace
        self._audit_log: list[dict[str, Any]] = []  # In-memory audit trail for this session

    def _load_audit_history(self) -> list[dict[str, Any]]:
        """Load persistent audit history from workspace."""
        if not self.workspace:
            return []
        path = self.workspace / "memory" / "INTROSPECTION_AUDIT.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save_audit_entry(self, entry: dict[str, Any]):
        """Persist an audit entry."""
        self._audit_log.append(entry)
        if not self.workspace:
            return
        path = self.workspace / "memory" / "INTROSPECTION_AUDIT.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        # Keep last 100 entries to prevent bloat
        history = self._load_audit_history()
        history.append(entry)
        history = history[-100:]
        path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")

    async def _plan_checks(
        self,
        messages: list[dict[str, Any]],
        draft_content: str,
        tools_used: list[str],
    ) -> list[dict[str, Any]]:
        """
        PASS 1 — PLAN: Dynamically select which introspection rules are
        relevant to the current objective and deliverables.
        """
        # Extract signals from context
        tools_lower = [t.lower() for t in tools_used]
        draft_lower = (draft_content or "").lower()

        # Extract the user's original request from messages
        user_objective = ""
        for m in messages:
            if m.get("role") == "user" and not m.get("content", "").startswith("[SYSTEM"):
                user_objective = m.get("content", "")
                break

        # Smart rule selection based on context signals
        selected_rules = []
        for rule in INTROSPECTION_RULES:
            relevance_score = 0

            # Always include core quality & no-refusal checks
            if rule["id"] in ("R1_NO_REFUSAL", "R2_PREMATURE_STOP", "R7_OBJECTIVE_ALIGNMENT"):
                relevance_score = 10

            # Credential rules only if auth-related tools/context
            if "credential" in rule["tags"]:
                if any(k in draft_lower for k in ["login", "password", "credential", "auth", "sign in"]):
                    relevance_score = 8
                elif any("credential" in t for t in tools_lower):
                    relevance_score = 8

            # Learning rules if novel complex work was done
            if "learning" in rule["tags"]:
                if len(tools_used) >= 3:
                    relevance_score = max(relevance_score, 5)

            # Evolution rules if errors or limitations detected
            if "evolution" in rule["tags"]:
                if any(k in draft_lower for k in ["error", "failed", "cannot", "limitation", "missing"]):
                    relevance_score = max(relevance_score, 7)

            # Discovery rules if new apps/files/repos mentioned
            if "discovery" in rule["tags"]:
                if any(k in draft_lower for k in ["found", "discovered", "installed", "new app", "repository"]):
                    relevance_score = max(relevance_score, 6)

            if relevance_score > 0:
                selected_rules.append({**rule, "_relevance": relevance_score})

        # Sort by relevance (highest first)
        selected_rules.sort(key=lambda r: r["_relevance"], reverse=True)

        logger.info(
            "Introspection planned {} / {} checks for this turn: {}",
            len(selected_rules), len(INTROSPECTION_RULES),
            [r["id"] for r in selected_rules]
        )

        return selected_rules

    def _build_adaptive_prompt(
        self,
        planned_rules: list[dict[str, Any]],
        user_objective: str,
        course_correction: str = "",
    ) -> str:
        """Build a dynamic supervisor prompt from the planned rules."""

        rules_text = "\n".join(
            f"{i+1}. [{r['id']}] {r['check']}"
            for i, r in enumerate(planned_rules)
        )

        audit_context = ""
        if self._audit_log:
            recent = self._audit_log[-5:]
            rejection_rate = sum(1 for a in recent if not a.get("approved")) / len(recent)
            audit_context = (
                f"\n[AUDIT CONTEXT]\n"
                f"Recent rejection rate: {rejection_rate:.0%}\n"
                f"Last {len(recent)} verdicts: {[a.get('verdict') for a in recent]}\n"
            )

        correction_block = ""
        if course_correction:
            correction_block = (
                f"\n[COURSE CORRECTION — PRIORITY OVERRIDE]\n"
                f"Previous introspection feedback was insufficient. The gap between the "
                f"user's ACTUAL objective and what was delivered has WIDENED. You must:\n"
                f"{course_correction}\n"
            )

        return (
            "You are the Adaptive Introspection Supervisor for an autonomous AI agent.\n"
            "Your job is to review the agent's DRAFT RESPONSE and its RECENT EXECUTION HISTORY.\n"
            "The agent possesses FULL capabilities, including a 'browser' tool, "
            "credential vault tools, and evolution tools.\n\n"
            f"[USER'S ORIGINAL OBJECTIVE]\n{user_objective}\n\n"
            f"[PLANNED CHECKS — ordered by relevance]\n{rules_text}\n\n"
            f"[FINAL META-CHECK]\n"
            f"After running all planned checks, perform THE DELIVERABLES MATRIX:\n"
            f"- Compare what the user ASKED for vs what the agent ACTUALLY delivered.\n"
            f"- Identify any GAP between objective and deliverable.\n"
            f"- If a gap exists, REJECT and provide specific instructions to close the gap.\n"
            f"- Consider CONSTRAINTS: time, tool limitations, API availability.\n"
            f"{audit_context}{correction_block}\n"
            "You MUST output raw JSON matching exactly this format:\n"
            "{\n"
            '  "is_approved": true/false,\n'
            '  "reasoning": "brief explanation of why",\n'
            '  "rules_triggered": ["list of rule IDs that caused concerns"],\n'
            '  "deliverables_gap": "describe any gap between objective and actual output (empty if none)",\n'
            '  "constraints_noted": ["any constraints that affected the evaluation"],\n'
            '  "feedback": "If false, provide explicit instructions. (If true, leave empty)"\n'
            "}"
        )

    async def evaluate(
        self,
        messages: list[dict[str, Any]],
        draft_content: str,
        tools_used: list[str],
        publish_progress: Optional[Callable[[str], Awaitable[None]]] = None,
        max_correction_passes: int = 2,
    ) -> Tuple[bool, str]:
        """
        Adaptive evaluation with planning, audit, and course correction.

        1. PLAN: Select relevant rules for this context.
        2. EVALUATE: Run the planned checks.
        3. AUDIT: Track which rules triggered and whether correction improved output.
        4. COURSE-CORRECT: If re-evaluation after feedback still fails, escalate.
        """
        # Extract user objective
        user_objective = ""
        for m in messages:
            if m.get("role") == "user" and not m.get("content", "").startswith("[SYSTEM"):
                user_objective = m.get("content", "")
                break

        # PASS 1: Plan which checks to run
        planned_rules = await self._plan_checks(messages, draft_content, tools_used)

        if not planned_rules:
            logger.info("No introspection checks planned — auto-approving.")
            return True, ""

        # PASS 2: Evaluate with planned rules
        course_correction = ""
        for attempt in range(max_correction_passes):
            try:
                system_prompt = self._build_adaptive_prompt(
                    planned_rules, user_objective, course_correction
                )

                recent_context = json.dumps(messages[-6:], indent=2, ensure_ascii=False)
                user_prompt = (
                    f"--- RECENT CONTEXT ---\n{recent_context}\n\n"
                    f"--- TOOLS USED THIS TURN ---\n{tools_used}\n\n"
                    f"--- DRAFT RESPONSE TO EVALUATE ---\n{draft_content}\n"
                )

                eval_messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]

                response = await self.provider.chat(
                    messages=eval_messages,
                    model=self.model,
                    temperature=0.1,
                    max_tokens=1500,
                )

                content = response.content or "{}"
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]

                result = json_repair.loads(content.strip())

                is_approved = result.get("is_approved", True)
                feedback = result.get("feedback", "")
                reasoning = result.get("reasoning", "")
                rules_triggered = result.get("rules_triggered", [])
                deliverables_gap = result.get("deliverables_gap", "")
                constraints = result.get("constraints_noted", [])

                # AUDIT: Record this evaluation
                audit_entry = {
                    "timestamp": time.time(),
                    "attempt": attempt + 1,
                    "approved": is_approved,
                    "verdict": "APPROVED" if is_approved else "REJECTED",
                    "rules_planned": [r["id"] for r in planned_rules],
                    "rules_triggered": rules_triggered,
                    "deliverables_gap": deliverables_gap,
                    "constraints": constraints,
                    "objective_snippet": user_objective[:100],
                }
                self._save_audit_entry(audit_entry)

                if not is_approved:
                    logger.warning(
                        "Introspection REJECTED (pass %d). Rules: %s. Reason: %s",
                        attempt + 1, rules_triggered, reasoning
                    )
                    if publish_progress:
                        gap_note = f"\nDeliverables Gap: {deliverables_gap}" if deliverables_gap else ""
                        constraint_note = f"\nConstraints: {', '.join(constraints)}" if constraints else ""
                        await publish_progress(
                            f"🔍 **Supervisor (Pass {attempt + 1}):** Rejecting draft.\n"
                            f"Rules Triggered: {', '.join(rules_triggered)}\n"
                            f"Reason: {reasoning}{gap_note}{constraint_note}\n"
                            f"Action: Forcing self-correction."
                        )

                    if attempt < max_correction_passes - 1:
                        # COURSE-CORRECT: Build escalation context for next pass
                        course_correction = (
                            f"Previous rejection on pass {attempt + 1} was based on: {reasoning}\n"
                            f"Rules triggered: {rules_triggered}\n"
                            f"Deliverables gap identified: {deliverables_gap}\n"
                            f"The agent will attempt to self-correct. On this pass, be STRICTER about "
                            f"verifying the gap is actually closed. If the same gap persists, escalate."
                        )
                        continue

                    return False, feedback

                logger.info("Introspection APPROVED on pass %d", attempt + 1)
                return True, ""

            except Exception as e:
                logger.error("Introspection pass %d failed: %s", attempt + 1, e)
                # Record the failure in audit
                self._save_audit_entry({
                    "timestamp": time.time(),
                    "attempt": attempt + 1,
                    "approved": True,
                    "verdict": "ERROR_DEFAULT_APPROVE",
                    "error": str(e),
                })
                return True, ""

        return True, ""

    def get_audit_summary(self) -> str:
        """Generate a human-readable audit summary for the session."""
        if not self._audit_log:
            return "No introspection audits recorded this session."

        total = len(self._audit_log)
        rejections = sum(1 for a in self._audit_log if not a.get("approved"))
        approvals = total - rejections

        all_triggered = []
        for a in self._audit_log:
            all_triggered.extend(a.get("rules_triggered", []))

        # Count rule trigger frequency
        rule_freq = {}
        for r in all_triggered:
            rule_freq[r] = rule_freq.get(r, 0) + 1

        lines = [
            "=== INTROSPECTION AUDIT SUMMARY ===",
            f"Total evaluations: {total}",
            f"Approved: {approvals} | Rejected: {rejections}",
            f"Rejection rate: {rejections/total:.0%}" if total > 0 else "",
            "",
            "--- Most Triggered Rules ---",
        ]
        for rule, count in sorted(rule_freq.items(), key=lambda x: -x[1]):
            lines.append(f"  {rule}: {count} triggers")

        gaps = [a.get("deliverables_gap", "") for a in self._audit_log if a.get("deliverables_gap")]
        if gaps:
            lines.append("")
            lines.append("--- Deliverables Gaps Detected ---")
            for g in gaps[-5:]:
                lines.append(f"  • {g[:100]}")

        return "\n".join(lines)
