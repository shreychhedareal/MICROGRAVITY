from abc import ABC, abstractmethod
from typing import Type, Any
from pydantic import BaseModel, Field
import logging

from pipeline.executor import PipelineExecutor, LLMExecutor
from pipeline.hypothesis_engine import HypothesisEngine
from core.fsm import AgentFSM, AgentState

logger = logging.getLogger(__name__)

class BaseSeekerAgent(ABC):
    """
    Abstract Base Class for all Seeker Agents in the Swarm.
    Enforces the execution pipeline, including validation and retries.
    """
    
    def __init__(self, name: str, description: str, model_name: str = "gpt-4o-mini"):
        self.name = name
        self.description = description
        self.pipeline = PipelineExecutor(LLMExecutor(model_name=model_name))
        self.fsm = AgentFSM(agent_name=self.name)
        
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The core persona and strict instructions for this agent."""
        pass
        
    @property
    @abstractmethod
    def output_schema(self) -> Type[BaseModel]:
        """The strict Pydantic schema this agent must adhere to."""
        pass
        
    @abstractmethod
    def run_tools(self, parsed_objective: BaseModel) -> Any:
        """
        Executes the actual tools (shell, API, etc.) using the dynamically generated parameters.
        """
        pass
        
    def execute(self, objective: str, context: str = "") -> Any:
        """
        The main lifecycle method called by the Central Operator.
        """
        logger.info(f"Assigned objective to {self.name}: {objective}")
        
        # 1. Construct input
        user_prompt = f"OBJECTIVE:\n{objective}\n\nCONTEXT:\n{context}\n\nRespond strictly with JSON matching the required schema."
        
        # 2. FSM Start
        self.fsm.transition(AgentState.OPERATIONAL, "Commencing generation pipeline.")
        
        try:
            parsed_plan = self.pipeline.execute_with_validation(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                schema_class=self.output_schema
            )
            
            logger.info(f"{self.name} generated valid plan.")
            
            # 3. Operational Mode: Execute the derived plan
            result = self.run_tools(parsed_plan)
            
            # 4. Hypothesis Engine: Compare Anticipated vs Actual
            hypothesis_passed = True
            if hasattr(parsed_plan, "anticipated_result"):
                hypothesis_passed = HypothesisEngine.evaluate(parsed_plan.anticipated_result, result)
            
            # 5. Determine State based on execution and hypothesis
            self.fsm.handle_execution_result(is_valid_schema=True, hypothesis_passed=hypothesis_passed, retries_exhausted=False)
            
            if self.fsm.current_state in [AgentState.ALTERNATIVE_DECISION, AgentState.HANDOFF]:
                return {
                    "status": "failure",
                    "agent": self.name,
                    "fsm_state": self.fsm.current_state.value,
                    "error": "Hypothesis Failed: Actual execution deviated significantly from anticipated result.",
                    "actual_result": result,
                    "history": self.fsm.transition_history
                }
            
            return {
                "status": "success",
                "agent": self.name,
                "fsm_state": self.fsm.current_state.value,
                "plan": parsed_plan.model_dump(),
                "result": result,
                "history": self.fsm.transition_history
            }
            
        except Exception as e:
            # Handle severe validation/schema failures (Feedback mode failed exhaustively)
            logger.error(f"{self.name} failed execution: {e}")
            self.fsm.handle_execution_result(is_valid_schema=False, hypothesis_passed=False, retries_exhausted=True)
            return {
                "status": "failure",
                "agent": self.name,
                "error": str(e)
            }
