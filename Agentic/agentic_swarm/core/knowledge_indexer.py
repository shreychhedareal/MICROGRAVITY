import logging
from typing import Dict, Any, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class IndexedStrategy(BaseModel):
    objective_pattern: str
    winning_dag: List[Dict[str, str]]
    required_tools: List[str]
    performance_grade: str

class KnowledgeIndexer:
    """
    The Librarian of Exploitation.
    Captures, indexes, and retrieves optimized execution strategies. 
    Allows the Swarm to exploit proven methods rather than reinventing them.
    """
    def __init__(self, memory_adapter: Any):
        self.memory = memory_adapter
        self.indexed_strategies: Dict[str, IndexedStrategy] = {}
        
    def capture_and_index(self, pattern: str, strategy: IndexedStrategy):
        """Saves a fully graded and optimized strategy into long-term exploitation memory."""
        self.indexed_strategies[pattern] = strategy
        self.memory.save_state(f"indexed_strategy:{pattern}", strategy.model_dump())
        logger.info(f"📚 Knowledge Indexed: Exploitable Strategy for '{pattern}' has been captured.")
        
    def exploit_strategy(self, current_objective: str) -> IndexedStrategy | None:
        """
        Searches the index for a matching proven strategy.
        In MVP this is a basic keyword match; in production, this is a Vector DB semantic search.
        """
        for pattern, strategy in self.indexed_strategies.items():
            if pattern.lower() in current_objective.lower():
                logger.info(f"🎯 Exploitation Opportunity Found! Exact match for: {pattern}")
                return strategy
        return None
