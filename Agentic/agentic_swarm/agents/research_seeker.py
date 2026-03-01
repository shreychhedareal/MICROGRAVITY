from pydantic import BaseModel, Field
import logging
from typing import Any, List

from agents.base import BaseSeekerAgent

logger = logging.getLogger(__name__)

class ResearchSchema(BaseModel):
    search_queries: List[str] = Field(description="List of search engine query strings to explore.")
    expected_information: str = Field(description="Summary of the core knowledge the agent is trying to extract.")

class ResearchSeeker(BaseSeekerAgent):
    """
    Research Seeker: A generalized agent that explores open-ended questions by querying the web and summarizing data.
    """
    def __init__(self, model_name: str = "gpt-4o-mini"):
        super().__init__(
            name="ResearchSeeker",
            description="Gathers information, performs programmatic web searches, and distills raw data into insights.",
            model_name=model_name
        )

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Research Seeker, a generalized agent for gathering knowledge.\n"
            "Break down the user's objective into distinct search queries that will yield the highest quality information.\n"
            "CRITICAL:\n"
            "1. Output valid JSON matching the schema.\n"
            "2. search_queries must be targeted and specific."
        )

    @property
    def output_schema(self) -> type[BaseModel]:
        return ResearchSchema

    def run_tools(self, parsed_objective: BaseModel) -> Any:
        research_data: ResearchSchema = parsed_objective
        logger.info(f"Dispatching research queries: {research_data.search_queries}")
        
        # Mock web crawling / APIs (e.g. Tavily, Serper, Google Search API)
        return {
            "queries_executed": research_data.search_queries,
            "synthesized_report": f"Based on simulated research targeting '{research_data.expected_information}', the gathered intelligence suggests standard approaches align with current best practices.",
            "sources": ["https://example.com/docs", "https://example.com/api"]
        }
