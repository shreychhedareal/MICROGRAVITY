import logging
import random
from typing import Dict, Any, Type
from agents.base import BaseSeekerAgent

logger = logging.getLogger(__name__)

class AgentBuilder:
    """
    Manages dynamic instantiation, enhancement, and alternative versions of Seekers.
    Facilitates A/B testing of different prompts or models for the same capability.
    """
    def __init__(self):
        # A dictionary mapping a capability name to a list of available agent versions
        # e.g. {"Coding": [CodingSeeker_v1, CodingSeeker_v2]}
        self.capability_versions: Dict[str, list[BaseSeekerAgent]] = {}
        
    def register_version(self, capability: str, agent_instance: BaseSeekerAgent):
        """Registers an alternative version of an agent for a specific capability."""
        if capability not in self.capability_versions:
            self.capability_versions[capability] = []
        self.capability_versions[capability].append(agent_instance)
        logger.info(f"Registered {agent_instance.name} for capability '{capability}'. Total versions: {len(self.capability_versions[capability])}")

    def route_ab_test(self, capability: str) -> BaseSeekerAgent:
        """
        Retrieves an agent for a capability using A/B testing distribution.
        In this MVP, uses a random split.
        """
        versions = self.capability_versions.get(capability, [])
        if not versions:
            raise ValueError(f"No agents registered for capability: {capability}")
            
        if len(versions) == 1:
            return versions[0]
            
        # A/B testing: uniformly random distribution between available versions
        selected_agent = random.choice(versions)
        logger.info(f"A/B Test Router: Selected {selected_agent.name} for capability '{capability}'.")
        return selected_agent
