import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from agents.base import BaseSeekerAgent

logger = logging.getLogger(__name__)

class GradedStrategy(BaseModel):
    strategy_id: str = Field(description="Identifier for the alternative strategy.")
    execution_time_score: int = Field(description="1-10 score for speed and latency.")
    reliability_score: int = Field(description="1-10 score for stability and error resistance.")
    resource_weight_score: int = Field(description="1-10 score for efficiency of tokens and memory.")
    overall_grade: str = Field(description="A+, B-, C, etc.")
    justification: str = Field(description="The academic reasoning for this grade.")

class StrategyGradingSchema(BaseModel):
    winning_strategy_id: str = Field(description="The ID of the highest graded strategy.")
    grades: List[GradedStrategy] = Field(description="Individual grades for each explored alternative.")
    recommended_exploitation: str = Field(description="How the Swarm should exploit this winner in the future.")

class StrategyGrader(BaseSeekerAgent):
    """
    The A/B Tester / Academic.
    Explores alternative approaches to a problem and grades them against each other.
    """
    def __init__(self, model_name: str = "gpt-4o"):
        super().__init__(
            name="StrategyGrader",
            description="Explores alternative execution strategies and formally grades them for optimization.",
            model_name=model_name
        )

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Strategy Grader, the Swarm's Academic Evaluator.\n"
            "You review multiple alternative approaches (e.g., Script A vs Script B, or DAG Path 1 vs DAG Path 2).\n"
            "Given the performance logs of these alternatives:\n"
            "1. Grade each strategy strictly on Time, Reliability, and Resource Weight.\n"
            "2. Identify the single Winning Strategy.\n"
            "3. Formulate how this winning strategy should be 'exploited' (used by default) going forward.\n"
            "Output the strict JSON grading schema."
        )

    @property
    def output_schema(self) -> type[BaseModel]:
        return StrategyGradingSchema

    def run_tools(self, plan: StrategyGradingSchema) -> Any:
        logger.info(f"⚖️ Grading Complete. Winner: {plan.winning_strategy_id} | Exploitation: {plan.recommended_exploitation[:50]}...")
        return plan.model_dump()
