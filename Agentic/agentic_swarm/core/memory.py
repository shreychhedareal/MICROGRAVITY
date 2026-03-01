import uuid
import datetime
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# --- New Meta-Cognitive Schemas ---

class IdeaOrBottleneck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    agent_source: str = Field(description="The agent that recorded this.")
    category: str = Field(description="'idea' or 'bottleneck'")
    content: str = Field(description="The actual observation or suggestion.")
    context_ref: Optional[str] = Field(default=None, description="ID of the execution trace this relates to.")

class InsightMetadata(BaseModel):
    povs: List[str] = Field(default_factory=list, description="Points of view or perspectives.")
    metrics: List[str] = Field(default_factory=list, description="Metrics evaluated.")
    scopes: List[str] = Field(default_factory=list, description="Operational, temporal, or systemic scopes.")
    scales: str = Field(default="", description="Scales or orders of magnitude (e.g., 'Micro', 'Macro', '1000s of requests').")
    likelihood: str = Field(default="", description="Likelihood or probability context.")
    mood_emotion: str = Field(default="", description="Mood/emotion (e.g., 'Aggressive', 'Cautious', 'Exploratory').")
    intent: str = Field(default="", description="The fundamental intent behind deriving the insight.")

class DerivedInsight(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    topic: str = Field(description="The functional area this insight relates to (e.g., 'API Parsing', 'Resource Allocation').")
    insight: str = Field(description="The concrete, derived fact or strategy (e.g., 'Always use BS4 for html over Regex').")
    source_agent: str = Field(description="The meta-agent that researched/derived this.")
    metadata: InsightMetadata = Field(default_factory=InsightMetadata)

class ProcessIP(BaseModel):
    ip_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(description="A descriptive name for this isolated process.")
    path_function: List[Dict[str, Any]] = Field(description="The exact sequence of tool/agent calls that succeeded.")
    state_delta: str = Field(description="The net change to the environment state caused by this path.")
    cost_estimate: float = Field(default=0.0, description="Tokens or time cost to run this IP.")
    success_rate: float = Field(default=1.0, description="Historical reliability of this specific IP sequence.")

class MemoryAdapter:
    """
    Enhanced Memory Database handling Short-Term (Scratchpad), Long-Term (Ledger),
    and Subconscious (Idea/Bottleneck Pools & Process IPs).
    """
    def __init__(self):
        # Execution State
        self.scratchpad: Dict[str, Any] = {}
        self.ledger: List[Dict[str, Any]] = []
        
        # Meta-Cognitive Subconscious
        self.idea_pool: List[IdeaOrBottleneck] = []
        self.bottleneck_pool: List[IdeaOrBottleneck] = []
        self.derived_insights: List[DerivedInsight] = []
        
        # Experiential Internalization
        self.process_ips: Dict[str, ProcessIP] = {}

    def save_state(self, key: str, value: Any):
        self.scratchpad[key] = value
        
    def get_state(self, key: str) -> Any:
        return self.scratchpad.get(key)
        
    def log_execution(self, caller: str, target: str, input_data: Any, result: Any) -> str:
        trace_id = str(uuid.uuid4())
        trace = {
            "id": trace_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "caller": caller,
            "target": target,
            "input": input_data,
            "result": result
        }
        self.ledger.append(trace)
        logger.info(f"Ledger Updated: {caller} -> {target} [{trace_id}]")
        return trace_id

    def get_execution_history(self) -> List[Dict[str, Any]]:
        return self.ledger

    # --- Meta-Cognitive Methods ---

    def register_subconscious_thought(self, agent_source: str, category: str, content: str, trace_id: str = None):
        """Allows agents to drop asynchronous ideas or complain about bottlenecks."""
        thought = IdeaOrBottleneck(
            agent_source=agent_source,
            category=category,
            content=content,
            context_ref=trace_id
        )
        if category == "idea":
            self.idea_pool.append(thought)
            logger.info(f"💡 Idea added to pool from {agent_source}: {content[:50]}...")
        elif category == "bottleneck":
            self.bottleneck_pool.append(thought)
            logger.warning(f"⚠️ Bottleneck recorded from {agent_source}: {content[:50]}...")

    def internalize_process_ip(self, name: str, path_function: List[Dict], state_delta: str, cost: float) -> str:
        """Saves a successfully executed sequence of steps as an isolated, repeatable Process IP."""
        ip = ProcessIP(
            name=name,
            path_function=path_function,
            state_delta=state_delta,
            cost_estimate=cost
        )
        self.process_ips[ip.ip_id] = ip
        logger.info(f"🧠 Process IP Internalized: '{name}' [{ip.ip_id}]")
        return ip.ip_id

    def get_available_process_ips(self) -> Dict[str, ProcessIP]:
        return self.process_ips

    def register_derived_insight(self, topic: str, insight: str, source_agent: str, metadata: Dict[str, Any] = None):
        """Saves a concrete meta-cognitive insight for future planning use."""
        md_obj = InsightMetadata(**metadata) if metadata else InsightMetadata()
        di = DerivedInsight(topic=topic, insight=insight, source_agent=source_agent, metadata=md_obj)
        self.derived_insights.append(di)
        logger.info(f"💡 Derived Insight Captured via {source_agent}: {insight[:60]}...")

    def extract_insights(self, query_objective: str) -> str:
        """Extracts text insights strictly relevant to the current objective string, including rich metadata."""
        relevant = []
        for di in self.derived_insights:
            # Simple keyword overlap for MVP (in prod, use Vector DB similarity)
            if any(word.lower() in query_objective.lower() for word in di.topic.split()):
                meta_str = f"PoVs: {di.metadata.povs} | Scopes: {di.metadata.scopes} | Mood: {di.metadata.mood_emotion} | Intent: {di.metadata.intent} | Likelihood: {di.metadata.likelihood}"
                relevant.append(f"[{di.topic}] (Meta: {meta_str})\n-> Insight: {di.insight}")
        
        return "\n\n".join(relevant) if relevant else "No specific past insights found."

    def get_all_insights(self) -> List[DerivedInsight]:
        """Returns the full insights library for deliberate correlation screening."""
        return self.derived_insights
