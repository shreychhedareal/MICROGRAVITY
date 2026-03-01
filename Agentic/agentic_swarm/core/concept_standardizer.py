import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from core.memory import MemoryAdapter

logger = logging.getLogger(__name__)

class StandardizedConcept(BaseModel):
    raw_input: str
    standardized_term: str
    actionable_protocol: str

class ConceptStandardizer:
    """
    Middleware that intercepts chaotic environmental outputs or errors and maps them to standard terms.
    E.g. "TypeError in module X" -> "[Immunity Threat: Execution Crash]" -> triggers isolation protocol.
    """
    
    # Pre-programmed taxonomy mappings. In a real system, this could use a local fast NLP classifier
    TAXONOMY_MAP = {
        "error": "Immunity_Threat:Execution_Anomaly",
        "exception": "Immunity_Threat:Execution_Anomaly",
        "timeout": "Immunity_Threat:Resource_Exhaustion",
        "unauthorized": "Immunity_Threat:Access_Violation",
        "repetitive": "Bottleneck:Purposeless_Loop",
    }
    
    PROTOCOL_MAP = {
        "Immunity_Threat:Execution_Anomaly": "Isolate agent state; Request QASeeker triage.",
        "Immunity_Threat:Resource_Exhaustion": "Pause target process; Request DevOpsSeeker assessment.",
        "Immunity_Threat:Access_Violation": "Halt path execution; Request human-in-the-loop override.",
        "Bottleneck:Purposeless_Loop": "Terminate recursive loop; Re-evaluate Idea Pool.",
        "Unmapped_Phenomenon": "Log for MetaCognitive review."
    }

    @staticmethod
    def standardize(raw_output: str) -> StandardizedConcept:
        """
        Takes raw messy output from a Seeker or the environment and standardizes it.
        """
        raw_lower = raw_output.lower()
        matched_term = "Unmapped_Phenomenon"
        
        for keyword, term in ConceptStandardizer.TAXONOMY_MAP.items():
            if keyword in raw_lower:
                matched_term = term
                break
                
        protocol = ConceptStandardizer.PROTOCOL_MAP.get(matched_term, "Log and continue.")
        
        standardized = StandardizedConcept(
            raw_input=raw_output,
            standardized_term=matched_term,
            actionable_protocol=protocol
        )
        
        if matched_term != "Unmapped_Phenomenon":
            logger.warning(f"🛡️ Concept Standardized: '{matched_term}'. Triggering Protocol: '{protocol}'")
            
        return standardized
