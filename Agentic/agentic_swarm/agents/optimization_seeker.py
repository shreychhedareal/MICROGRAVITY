import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from agents.base import BaseSeekerAgent

logger = logging.getLogger(__name__)

class ImprovementDirective(BaseModel):
    target_type: str = Field(description="'AGENT_PERSONA', 'CUSTOM_SCRIPT', or 'TOOL_REGISTRY'.")
    target_name: str = Field(description="The name of the agent or tool being upgraded.")
    current_flaw: str = Field(description="Why the current version is sub-optimal.")
    improvement_strategy: str = Field(description="The exact strategy/refactoring required to fix it.")
    explicit_code_or_prompt: str = Field(default="", description="The new system prompt for an agent, or rewritten code for a script.")

class OptimizationPlanSchema(BaseModel):
    directives: List[ImprovementDirective] = Field(description="List of concrete strategies to update the Swarm's performance.")
    anticipated_impact: str = Field(description="Expected ROI on execution time, reliability, or token usage.")
    derived_insights: List[Dict[str, Any]] = Field(default_factory=list, description="New structural insights generated from this optimization. Dict includes 'topic', 'insight', and 'metadata'.")

class OptimizationSeeker(BaseSeekerAgent):
    """
    The Architect of Buildup & Improvement.
    Takes grades from StrategyGrader or bottlenecks from ProcessAnalyzer, 
    and formulates explicit Performance Improvement Strategies.
    """
    def __init__(self, memory_adapter: Any, model_name: str = "gpt-4o"):
        super().__init__(
            name="OptimizationSeeker",
            description="Formulates concrete performance improvement strategies and code refactors for the Swarm.",
            model_name=model_name
        )
        self.memory = memory_adapter

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Optimization Seeker.\n"
            "You receive analysis and grades regarding the Swarm's performance.\n"
            "Your job is to formulate concrete 'Performance Improvement Strategies'.\n"
            "If an Agent is inefficient, write a new System Prompt for it.\n"
            "If a custom script is slow, write a refactored version of the code.\n"
            "If a tool is being misused, write a new 'When-to' heuristic for the Tool Registry.\n"
            "Output the strict JSON optimization directives."
        )

    @property
    def output_schema(self) -> type[BaseModel]:
        return OptimizationPlanSchema

    def run_tools(self, plan: OptimizationPlanSchema) -> Any:
        logger.info(f"📈 Optimization Strategy formulated! Directives: {len(plan.directives)}")
        for directive in plan.directives:
            logger.info(f"  -> Upgrading [{directive.target_type}] {directive.target_name}: {directive.improvement_strategy[:50]}...")
            # In a full run, this would save the code to the agent_builder or write the newly refactored script.
            
        for di in plan.derived_insights:
            self.memory.register_derived_insight(
                topic=di.get("topic", "Optimization"),
                insight=di.get("insight", "Unspecified insight."),
                source_agent=self.name,
                metadata=di.get("metadata", {})
            )
            
        return plan.model_dump()
