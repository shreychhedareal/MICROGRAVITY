from enum import Enum
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AgentState(Enum):
    IDLE = "IDLE"                            # Waiting for assignment
    OPERATIONAL = "OPERATIONAL"              # Normal execution
    FEEDBACK_PROCESSING = "FEEDBACK"         # Internal self-correction loop
    ALTERNATIVE_DECISION = "ALTERNATIVE"     # Swapping logic/objective due to block
    HANDOFF = "HANDOFF"                      # Escalating to Operator or Human
    COMPLETED = "COMPLETED"                  # Successful completion
    FAILED = "FAILED"                        # Terminal failure

class AgentFSM:
    """
    Finite State Machine managing the cognitive state of a Seeker Agent.
    Allows dynamic transitions based on execution mechanics and hypothesis validation.
    """
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.current_state: AgentState = AgentState.IDLE
        self.transition_history = []
        
    def transition(self, new_state: AgentState, reason: str = ""):
        logger.info(f"[{self.agent_name} FSM] Transition: {self.current_state.value} -> {new_state.value}. Reason: {reason}")
        self.transition_history.append({
            "from": self.current_state.value,
            "to": new_state.value,
            "reason": reason
        })
        self.current_state = new_state

    def handle_execution_result(self, is_valid_schema: bool, hypothesis_passed: bool, retries_exhausted: bool):
        """
        Determines the next cognitive state based on the immediate execution results.
        """
        if self.current_state == AgentState.IDLE:
            self.transition(AgentState.OPERATIONAL, "Commencing execution.")
            
        if not is_valid_schema:
            if retries_exhausted:
                self.transition(AgentState.HANDOFF, "Schema validation failed repeatedly. Escalating.")
            else:
                self.transition(AgentState.FEEDBACK_PROCESSING, "Schema invalid. Attempting internal self-correction.")
            return

        if not hypothesis_passed:
            if self.current_state == AgentState.ALTERNATIVE_DECISION:
                self.transition(AgentState.HANDOFF, "Alternative Decision also failed hypothesis. Escalating.")
            else:
                self.transition(AgentState.ALTERNATIVE_DECISION, "Hypothesis failed. Switching to alternative strategic mode.")
            return

        self.transition(AgentState.COMPLETED, "Execution complete and hypothesis confirmed.")
