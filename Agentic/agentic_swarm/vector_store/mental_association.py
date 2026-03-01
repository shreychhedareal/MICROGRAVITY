import math
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class VectorMath:
    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        dot_product = sum(a * b for a, b in zip(v1, v2))
        magnitude_v1 = math.sqrt(sum(a * a for a in v1))
        magnitude_v2 = math.sqrt(sum(b * b for b in v2))
        if magnitude_v1 == 0 or magnitude_v2 == 0:
            return 0.0
        return dot_product / (magnitude_v1 * magnitude_v2)

class MentalAssociationFaculty:
    """
    Replaces hardcoded dict lookups with Semantic Vector Embeddings mapping.
    Agents and Objectives are embedded in N-dimensional space.
    """
    def __init__(self):
        # In MVP, we use naive keyword bagging as pseudo-embeddings.
        # In Prod, this hooks into `litellm.embedding()` and MeiliSearch.
        self.agent_embeddings: Dict[str, List[float]] = {}
        
        # Pre-calculated pseudo-embeddings for known capabilities
        # Dimensions: [Code_Focus, SysAdmin_Focus, Research_Focus, Architect_Focus]
        self._seed_embeddings()

    def _seed_embeddings(self):
        self.agent_embeddings["SystemSeeker"] = [0.1, 0.9, 0.2, 0.1]
        self.agent_embeddings["QASeeker"] = [0.8, 0.4, 0.1, 0.3]
        self.agent_embeddings["DevOpsSeeker"] = [0.2, 0.9, 0.1, 0.4]
        self.agent_embeddings["ResearchSeeker"] = [0.1, 0.1, 0.9, 0.2]
        self.agent_embeddings["CodingSeeker"] = [0.9, 0.2, 0.2, 0.6]
        self.agent_embeddings["ArchitectureEstimator"] = [0.6, 0.4, 0.5, 0.9]

    def _pseudo_embed_objective(self, objective: str) -> List[float]:
        """Converts raw text into a naive 4D vector for cosine math."""
        text = objective.lower()
        v = [0.0, 0.0, 0.0, 0.0]
        
        # 0: Code Focus
        if any(w in text for w in ["code", "script", "function", "bug", "test"]): v[0] += 0.8
        # 1: SysAdmin Focus
        if any(w in text for w in ["system", "cron", "process", "file", "terminal"]): v[1] += 0.8
        # 2: Research Focus
        if any(w in text for w in ["find", "search", "gather", "what is"]): v[2] += 0.8
        # 3: Architect Focus
        if any(w in text for w in ["design", "pattern", "estimate", "hardware"]): v[3] += 0.8
        
        # Normalize slightly
        return [max(0.1, x) for x in v]

    def associate_best_agent(self, objective: str, available_agents: List[str], threshold: float = 0.5) -> str:
        """
        Uses semantic similarity to dynamically associate an objective with a cognitive agent node.
        """
        obj_vector = self._pseudo_embed_objective(objective)
        
        best_agent = None
        best_score = -1.0
        
        for agent_name in available_agents:
            if agent_name in self.agent_embeddings:
                score = VectorMath.cosine_similarity(obj_vector, self.agent_embeddings[agent_name])
                logger.debug(f"Association Score [{agent_name}]: {score}")
                if score > best_score:
                    best_score = score
                    best_agent = agent_name
                    
        if best_score >= threshold:
            logger.info(f"🧠 Mental Association mapping: '{objective[:20]}' -> mapped to [{best_agent}] (Score: {best_score:.2f})")
            return best_agent
            
        logger.warning("Mental Association failed to find a high-confidence agent mapping. Defaulting to Generalized Seeker.")
        return "ResearchSeeker" # Ultimate fallback
