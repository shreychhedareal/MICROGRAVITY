import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from agents.base import BaseSeekerAgent

logger = logging.getLogger(__name__)

class CorrelationEdge(BaseModel):
    insight_a: str = Field(description="The text of the first insight being correlated.")
    insight_b: str = Field(description="The text of the second insight being correlated.")
    relationship: str = Field(description="One of: REINFORCES, CONTRADICTS, GENERALIZES, SPECIALIZES, INDEPENDENT.")
    confidence: str = Field(description="How confident is this correlation? High, Medium, or Low.")
    emergent_pattern: str = Field(default="", description="If two insights together reveal a new higher-order pattern or rule, state it here.")

class CorrelationScreeningSchema(BaseModel):
    correlation_edges: List[CorrelationEdge] = Field(description="All discovered correlations between pairs of insights.")
    reinforced_rules: List[str] = Field(default_factory=list, description="Insights that are strongly reinforced by multiple independent sources.")
    contradictions: List[str] = Field(default_factory=list, description="Insights that directly contradict each other — requires resolution.")
    emergent_insights: List[str] = Field(default_factory=list, description="Entirely new higher-order patterns that emerged ONLY from cross-referencing.")
    screening_summary: str = Field(description="A concise executive summary of the correlation screening results for the planner.")

class InsightCorrelator(BaseSeekerAgent):
    """
    Deliberately screens the full insights library for correlations.
    Cross-references every insight against every other to find:
      - Reinforcements (multiple insights pointing to the same conclusion)
      - Contradictions (insights that conflict and need resolution)
      - Emergent patterns (new rules that only become visible when insights are compared)
    """
    def __init__(self, memory_adapter: Any, model_name: str = "gpt-4o"):
        super().__init__(
            name="InsightCorrelator",
            description="Screens the insights library for reinforcements, contradictions, and emergent correlations.",
            model_name=model_name
        )
        self.memory = memory_adapter

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Insight Correlator.\n"
            "You receive the FULL library of derived insights (each with rich metadata including PoVs, Scopes, Moods, Intents, Scales).\n"
            "Your job is to DELIBERATELY cross-reference every insight against every other.\n"
            "For each pair, determine the relationship:\n"
            "  - REINFORCES: Both insights point to the same conclusion from different angles.\n"
            "  - CONTRADICTS: The insights conflict. Flag for resolution.\n"
            "  - GENERALIZES: One insight is a broader version of the other.\n"
            "  - SPECIALIZES: One insight is a more specific case of the other.\n"
            "  - INDEPENDENT: No meaningful correlation.\n"
            "Additionally, look for EMERGENT PATTERNS — higher-order rules that ONLY become visible\n"
            "when you cross-reference multiple insights together. These are the most valuable.\n"
            "Finally, produce a concise screening_summary that the planner can consume.\n"
            "Output the strict JSON schema."
        )

    @property
    def output_schema(self) -> type[BaseModel]:
        return CorrelationScreeningSchema

    def run_tools(self, plan: CorrelationScreeningSchema) -> Any:
        reinforced = len(plan.reinforced_rules)
        contradictions = len(plan.contradictions)
        emergent = len(plan.emergent_insights)

        logger.info(
            f"🔗 Correlation Screening Complete. "
            f"Edges: {len(plan.correlation_edges)} | "
            f"Reinforced: {reinforced} | "
            f"Contradictions: {contradictions} | "
            f"Emergent Patterns: {emergent}"
        )

        if contradictions > 0:
            logger.warning(f"⚠️ {contradictions} CONTRADICTIONS detected in insights library! Requires resolution.")

        # Register any emergent insights back into memory
        for ei in plan.emergent_insights:
            self.memory.register_derived_insight(
                topic="Emergent Correlation",
                insight=ei,
                source_agent=self.name,
                metadata={
                    "povs": ["Cross-Referential"],
                    "scopes": ["Library-Wide"],
                    "mood_emotion": "Analytical",
                    "intent": "Emergent pattern discovered via deliberate correlation screening."
                }
            )

        return plan.model_dump()

    def build_library_context(self) -> str:
        """Formats the full insight library into a context string for the LLM."""
        all_insights = self.memory.get_all_insights()
        if not all_insights:
            return ""

        lines = []
        for i, di in enumerate(all_insights, 1):
            meta = di.metadata
            lines.append(
                f"INSIGHT #{i}:\n"
                f"  Topic: {di.topic}\n"
                f"  Text: {di.insight}\n"
                f"  Source: {di.source_agent}\n"
                f"  PoVs: {meta.povs} | Scopes: {meta.scopes} | Scale: {meta.scales}\n"
                f"  Mood: {meta.mood_emotion} | Intent: {meta.intent} | Likelihood: {meta.likelihood}"
            )
        return "\n\n".join(lines)
