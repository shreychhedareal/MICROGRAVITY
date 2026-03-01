import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from agents.base import BaseSeekerAgent

logger = logging.getLogger(__name__)

class ContextualDirective(BaseModel):
    original_insight: str = Field(description="The exact text of the raw insight.")
    is_applicable: bool = Field(description="Is this insight strictly applicable to the CURRENT objective based on scope, scale, mood, and intent?")
    reasoning: str = Field(description="Why it applies or doesn't apply based on the specific scope/mood/metric match.")
    translated_rule: str = Field(default="", description="If applicable, rewrite the insight into a strict mandate for the Planner.")

class InternalizationSchema(BaseModel):
    evaluated_insights: List[ContextualDirective] = Field(description="The evaluation of all raw insights.")
    final_contextual_injection: str = Field(description="A concise summary of ONLY the applicable translated rules to be fed to the Necessity Sensor.")

class InsightInternalizer(BaseSeekerAgent):
    """
    Evaluates raw historical insights for relevance against the current context
    and translates them into actionable planning directives.
    """
    def __init__(self, model_name: str = "gpt-4o"):
        super().__init__(
            name="InsightInternalizer",
            description="Evaluates the specific scope, context, and applicability of raw derived insights for active planning.",
            model_name=model_name
        )

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Insight Internalizer.\n"
            "Your job is to read raw historical insights (which include rich metadata like PoVs, Scopes, Moods, Intents, and Metrics) "
            "and strictly evaluate if they apply to the CURRENT OBJECTIVE's specific context.\n"
            "Do not blindly apply insights if the context, scope, or mood is fundamentally different from the original intent.\n"
            "For example, an insight with an 'Aggressive' mood and 'Macro' scale might not apply to a 'Cautious', 'Micro' objective.\n"
            "If an insight is applicable, translate it into a strict 'Translated Rule' for the active planner.\n"
            "If it is not applicable due to scope or metric mismatch, mark it as False and ignore it.\n"
            "Finally, summarize all applicable translated rules into a single injection text block."
            "\nOutput the strict JSON schema."
        )

    @property
    def output_schema(self) -> type[BaseModel]:
        return InternalizationSchema

    def run_tools(self, plan: InternalizationSchema) -> Any:
        applicable_count = sum(1 for d in plan.evaluated_insights if d.is_applicable)
        logger.info(f"🧠 Insight Internalization Complete. Evaluated: {len(plan.evaluated_insights)} | Applicable: {applicable_count}")
        return plan.model_dump()
