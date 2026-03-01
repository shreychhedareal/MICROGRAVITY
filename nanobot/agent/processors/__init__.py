"""Processor layer — advanced middleware for the agent swarm.

Provides intelligent caching, bulk I/O, speculative planning,
routing, incremental learning, awareness projection, and
architecture self-documentation.
"""

from nanobot.agent.processors.cache import IntelligentCache
from nanobot.agent.processors.bulk_io import BulkIOProcessor
from nanobot.agent.processors.speculative_planner import SpeculativePlanner
from nanobot.agent.processors.routing import RoutingMapper
from nanobot.agent.processors.learner import IncrementalLearner
from nanobot.agent.processors.awareness import AwarenessProjector
from nanobot.agent.processors.arch_knowledge import ArchitectureKnowledgeBase

__all__ = [
    "IntelligentCache",
    "BulkIOProcessor",
    "SpeculativePlanner",
    "RoutingMapper",
    "IncrementalLearner",
    "AwarenessProjector",
    "ArchitectureKnowledgeBase",
]
