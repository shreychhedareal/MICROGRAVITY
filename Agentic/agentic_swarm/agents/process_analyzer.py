import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from agents.base import BaseSeekerAgent

logger = logging.getLogger(__name__)

class ProcessAuditSchema(BaseModel):
    is_optimal: bool = Field(description="Was this execution path optimally efficient?")
    bottlenecks_identified: List[str] = Field(default_factory=list, description="Specific inefficient steps, redundant loops, or high-latency actions.")
    error_patterns: List[str] = Field(default_factory=list, description="Recurring errors or Immunity Threats triggered during execution.")
    suggested_alternatives: str = Field(default="", description="High-level suggestion on how to restructure the DAG or tool usage.")
    derived_insights: List[Dict[str, Any]] = Field(default_factory=list, description="List of dicts with 'topic', 'insight', and a 'metadata' dict containing povs, metrics, scopes, scales, likelihood, mood_emotion, and intent.")

class ProcessAnalyzer(BaseSeekerAgent):
    """
    The Historian / Auditor.
    Monitors the Execution Ledger to analyze how tasks were completed, 
    flagging redundant loops, excessive step counts, and sub-optimal tool usage.
    """
    def __init__(self, memory_adapter: Any, model_name: str = "gpt-4o"):
        super().__init__(
            name="ProcessAnalyzer",
            description="Analyzes historical execution ledgers to identify bottlenecks and structural inefficiencies.",
            model_name=model_name
        )
        self.memory = memory_adapter

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Process Analyzer. Your role is to audit the Swarm's Execution Ledger.\n"
            "You do NOT execute tasks. You analyze PAST executions.\n"
            "Given an execution log (DAG path, tools used, errors encountered):\n"
            "1. Evaluate if the process was optimal.\n"
            "2. Identify explicit bottlenecks (e.g., agent bounced between tools uselessly).\n"
            "3. Identify error patterns or frequent 'Alternative Decision Mode' triggers.\n"
            "4. Suggest high-level structural alternatives to eliminate the bottlenecks.\n"
            "Output the strict JSON audit schema."
        )

    @property
    def output_schema(self) -> type[BaseModel]:
        return ProcessAuditSchema

    def run_tools(self, plan: ProcessAuditSchema) -> Any:
        # The analyzer's action is formalizing the audit.
        logger.info(f"🔍 Audit Complete. Optimal: {plan.is_optimal}. Bottlenecks: {len(plan.bottlenecks_identified)}")
        if not plan.is_optimal:
            logger.warning(f"Process Analyzer flagged inefficiency: {plan.suggested_alternatives}")
            
        # Log newly derived meta-insights into memory
        for di in plan.derived_insights:
            self.memory.register_derived_insight(
                topic=di.get("topic", "General Research"),
                insight=di.get("insight", "Unspecified insight."),
                source_agent=self.name,
                metadata=di.get("metadata", {})
            )
            
        return plan.model_dump()
