import json
import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from agents.base import BaseSeekerAgent
from core.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

class ResourceBlueprintSchema(BaseModel):
    existing_tools_to_use: List[str] = Field(description="Names of existing tools from ToolRegistry to be used.")
    new_tools_to_create: List[str] = Field(description="Names/Purposes of new scripts, tools, or APIs that MUST be created to solve this.")
    existing_agents_to_use: List[str] = Field(description="List of existing specialized agents to invoke.")
    new_agents_to_create: List[str] = Field(default_factory=list, description="Proposals for entirely new Agent personas required.")
    dependency_graph: List[Dict[str, str]] = Field(description="Step by step DAG. (e.g. {'step': 1, 'agent': 'ActionSeeker', 'task': 'Write script X'})")
    creation_reasoning: str = Field(description="Why existing resources are insufficient, justifying the creation of new tools/agents.")
    estimated_time_seconds: int = Field(description="Estimated execution time in seconds.")
    computational_weight: str = Field(description="Low, Medium, or High.")
    anticipated_result: str = Field(default="", description="The overall expected change in the environment state.")

class NecessitySensor(BaseSeekerAgent):
    """
    Acts as the Pre-Frontal Cortex. Before execution begins, it intercepts the objective 
    and outputs a strict Resource Blueprint (DAG, Tools, Dependencies).
    """

    def __init__(self, tool_registry: ToolRegistry, available_agents: List[str], model_name: str = "gpt-4o"):
        super().__init__(
            name="NecessitySensor",
            description="Analyzes objectives to pre-compute dependencies and toolchain blueprints.",
            model_name=model_name
        )
        self.tool_registry = tool_registry
        self.available_agents = available_agents

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Necessity Sensor, the Resource Allocation brain of the Swarm.\n"
            "You do not execute tasks. You evaluate, analyze, and propose resource allocations.\n"
            "Given a user objective, you must figure out what is required to fulfill the objective.\n"
            "CRITICAL:\n"
            "1. If existing tools/agents are sufficient, allocate them.\n"
            "2. If they are insufficient, explicitly PROPOSE the creation of NEW agents, scripts, or APIs.\n"
            "3. Provide exactly how the ActionSeeker should build these new tools, or how the AgentBuilder should build new agents.\n"
            f"AVAILABLE AGENTS: {self.available_agents}\n"
            f"REGISTERED TOOLS:\n{self.tool_registry.get_all_summaries()}\n"
            "Output the strict JSON blueprint schema."
        )

    @property
    def output_schema(self) -> type[BaseModel]:
        return ResourceBlueprintSchema

    def run_tools(self, plan: ResourceBlueprintSchema) -> Any:
        # The Necessity Sensor doesn't run external tools. Its computation *is* the Blueprint.
        # So we just pass the plan straight through as the execution result.
        logger.info(f"🧠 Necessity Sensor generated Blueprint. Est Time: {plan.estimated_time_seconds}s | Weight: {plan.computational_weight}")
        return plan.model_dump()
