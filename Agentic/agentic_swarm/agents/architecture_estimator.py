from pydantic import BaseModel, Field
import logging
from typing import Any, List

from agents.base import BaseSeekerAgent

logger = logging.getLogger(__name__)

class ResourceEstimations(BaseModel):
    compilation_time_ms: int = Field(description="Estimated compilation or build time in milliseconds.")
    runtime_memory_mb: float = Field(description="Estimated peak runtime memory usage in Megabytes.")
    storage_footprint_mb: float = Field(description="Estimated disk storage footprint for binaries/assets.")

class DeploymentSizing(BaseModel):
    recommended_cpu_cores: float = Field(description="Recommended vCPUs for production deployment.")
    recommended_ram_gb: float = Field(description="Recommended RAM in GB for production deployment.")
    scaling_strategy: str = Field(description="Horizontal vs Vertical scaling recommendations and reasoning.")

class ArchitectureSchema(BaseModel):
    design_patterns: List[str] = Field(description="Identified or recommended software design patterns (e.g. 'Singleton', 'Strategy', 'Factory').")
    refactoring_suggestions: List[str] = Field(description="Specific suggestions for decoupling, abstractions, or better pattern adherence.")
    resource_estimates: ResourceEstimations = Field(description="Precise estimates of compilation speed and memory footprint.")
    hardware_sizing: DeploymentSizing = Field(description="Specific infrastructure and cloud deployment requirements.")

class ArchitectureEstimator(BaseSeekerAgent):
    """
    Architecture Estimator: Analyzes code structure to extract design patterns, suggest refactoring,
    and estimate system resource requirements (compilation, runtime, hardware deployments).
    """
    def __init__(self, model_name: str = "gpt-4o"):
        # We default to gpt-4o here because architectural analysis requires high reasoning
        super().__init__(
            name="ArchitectureEstimator",
            description="Analyzes design patterns, estimates compilation/memory loads, and sizes deployment hardware.",
            model_name=model_name
        )

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Architecture Estimator agent, a senior Staff/Principal Systems Engineer.\n"
            "Your job is to analyze code snippets or system blueprints and extract Deep Architectural Insights.\n"
            "You must:\n"
            "1. Identify structural Design Patterns used (or missing).\n"
            "2. Estimate the compilation/build time and runtime memory footprint.\n"
            "3. Calculate the ideal bare-metal or cloud hardware deployment sizing.\n"
            "CRITICAL:\n"
            "1. Output valid JSON matching the exact schema.\n"
            "2. Ensure resource estimates are realistic programmatic numbers."
        )

    @property
    def output_schema(self) -> type[BaseModel]:
        return ArchitectureSchema

    def run_tools(self, parsed_objective: BaseModel) -> Any:
        arch_data: ArchitectureSchema = parsed_objective
        logger.info(f"Architecture Analyzed! Patterns: {arch_data.design_patterns}")
        logger.info(f"Deployment sizing: {arch_data.hardware_sizing.recommended_cpu_cores} Cores / {arch_data.hardware_sizing.recommended_ram_gb} GB RAM")
        
        # In a real environment, this agent might actually trigger a dry-run build pipeline via the OS
        # to measure exact compilation times, or query AWS/GCP pricing calculators.
        
        return {
            "status": "success",
            "report_summary": "Architecture factored and resources estimated successfully.",
            "metrics": arch_data.model_dump()
        }
