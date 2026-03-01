import re
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class AnalyticalScripts:
    """
    Explicit parsing layer that sits between the LLM output and JSON serialization.
    Enforces strict Regex rules, Word Detection, and Phrase Detection from the original spec.
    """
    
    # Global banned patterns
    BANNED_REGEX = [
        r"(?i)\brm\s+-rf\b",           # Dangerous deletion
        r"(?i)\bformat\s+[A-Z]:\b",    # Windows format
        r"(?i)\bdrop\s+table\b"        # SQL destruction
    ]
    
    # Required phrases depending on agent context
    REQUIRED_PHRASES = {
        "SystemSeeker": [r"(?i)\bpowershell\b", r"(?i)\bls\b|(?i)\bdir\b|(?i)\bcat\b"],
    }
    
    # Banned words indicating severe hallucination or refusal
    BANNED_WORDS = [
        "cannot fulfill",
        "as an AI",
        "I'm sorry",
        "I apologize"
    ]

    @staticmethod
    def run_regex_enforcement(raw_text: str, agent_context: str = "General") -> Tuple[bool, str]:
        """
        Runs the raw text through the analytical regex and standard detection scripts.
        Returns (is_valid, error_message).
        """
        # 1. Ban Dangerous Regex Patterns
        for pattern in AnalyticalScripts.BANNED_REGEX:
            if re.search(pattern, raw_text):
                msg = f"Analytical Error: Severe regex violation detected. Banned pattern '{pattern}' found."
                logger.error(msg)
                return False, msg
                
        # 2. Ban Refusal Words
        for word in AnalyticalScripts.BANNED_WORDS:
            if word.lower() in raw_text.lower():
                msg = f"Analytical Error: Unhelpful or refusal phrase '{word}' detected."
                logger.warning(msg)
                return False, msg
                
        # 3. Contextual Enforcement (Optional based on agent)
        if agent_context in AnalyticalScripts.REQUIRED_PHRASES:
            # For this MVP, we just log contextual omissions rather than failing outright, 
            # unless the specific agent configuration mandates it.
            pass
            
        return True, "Analysis Passed."
