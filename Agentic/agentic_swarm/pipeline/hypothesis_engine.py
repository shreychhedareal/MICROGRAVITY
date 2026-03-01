import logging
from typing import Dict, Any
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

class HypothesisEngine:
    """
    Evaluates the 'Anticipated' result (set by the agent before execution) 
    against the 'Actual' result from the environment.
    """
    
    @staticmethod
    def evaluate(anticipated: str, actual_result: Any) -> bool:
        """
        Calculates the deviation between what the agent thought would happen 
        and what actually happened.
        """
        # In this MVP, we use naive keyword checking.
        # Real system: uses LLM semantic analysis or strict JSON diffs.
        actual_str = str(actual_result).lower()
        anticipated_str = anticipated.lower()
        
        # Extract keywords from the agent's hypothesis
        keywords = [word.strip() for word in anticipated_str.split() if len(word) > 4]
        
        # If the actual output doesn't contain any of the expected hallmarks
        hit_count = sum(1 for kw in keywords if kw in actual_str)
        
        if len(keywords) > 0 and hit_count == 0:
            logger.warning(f"Hypothesis Failed! Anticipated '{anticipated[:30]}...' but actual output did not match.")
            return False
            
        logger.info("Hypothesis Confirmed. Actual result aligns with anticipation.")
        return True
