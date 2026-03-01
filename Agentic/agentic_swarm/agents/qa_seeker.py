from pydantic import BaseModel, Field
import logging
from typing import Any

from agents.base import BaseSeekerAgent

logger = logging.getLogger(__name__)

class QASchema(BaseModel):
    target_file: str = Field(description="The path to the file to be analyzed or tested.")
    analysis_type: str = Field(description="The type of analysis to run: lint, unit_test, or code_review.")
    test_framework: str = Field(default="pytest", description="Testing framework to use, e.g. pytest.")
    
class QASeeker(BaseSeekerAgent):
    """
    Quality Assurance Seeker: Analyzes code, finds bugs, and runs test suites.
    """
    def __init__(self, model_name: str = "gpt-4o-mini"):
        super().__init__(
            name="QASeeker",
            description="Analyzes codebase errors, runs unit tests, and conducts static code reviews.",
            model_name=model_name
        )

    @property
    def system_prompt(self) -> str:
        return (
            "You are the QA Seeker agent. Your responsibility is to strictly analyze an objective "
            "related to code quality, bug finding, or test execution and configure the correct "
            "analysis pipeline.\n"
            "CRITICAL:\n"
            "1. Output valid JSON matching the exact schema.\n"
            "2. analysis_type must be 'lint', 'unit_test', or 'code_review'."
        )

    @property
    def output_schema(self) -> type[BaseModel]:
        return QASchema

    def run_tools(self, parsed_objective: BaseModel) -> Any:
        qa_data: QASchema = parsed_objective
        logger.info(f"Running QA ({qa_data.analysis_type}) on {qa_data.target_file}")
        
        # Mock execution logic: in a real implementation, this would trigger pytest or a linter
        result = f"Successfully executed simulated {qa_data.analysis_type} on {qa_data.target_file} using {qa_data.test_framework}."
        
        return {
            "file": qa_data.target_file,
            "status": "passed",
            "findings": ["No severe issues detected."],
            "message": result
        }
