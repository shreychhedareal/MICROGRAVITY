from typing import Dict, Any
import logging
from pydantic import BaseModel, Field

from core.memory import MemoryAdapter
from pipeline.executor import PipelineExecutor, LLMExecutor
from agents.system_seeker import SystemSeeker
from agents.qa_seeker import QASeeker
from agents.devops_seeker import DevOpsSeeker
from agents.research_seeker import ResearchSeeker
from agents.coding_seeker import CodingSeeker
from agents.architecture_estimator import ArchitectureEstimator
from agents.action_seeker import ActionSeeker
from agents.necessity_sensor import NecessitySensor
from agents.process_analyzer import ProcessAnalyzer
from agents.strategy_grader import StrategyGrader
from agents.optimization_seeker import OptimizationSeeker
from agents.insight_internalizer import InsightInternalizer
from agents.insight_correlator import InsightCorrelator
from core.concept_standardizer import ConceptStandardizer
from core.experiential_learning import ExperientialLearningModule
from vector_store.mental_association import MentalAssociationFaculty
from core.event_bus import DurableEventBus
from core.tool_registry import ToolRegistry
from core.knowledge_indexer import KnowledgeIndexer

logger = logging.getLogger(__name__)

class OperatorPlanSchema(BaseModel):
    selected_agent: str = Field(description="The name of the assigned agent (e.g. 'SystemSeeker').")
    sub_objective: str = Field(description="The specific prompt to pass to the agent.")
    reasoning: str = Field(description="Why this agent was selected.")

class SeekingOperator:
    """
    The Central Executive Brain of the Swarm.
    Responsible for Mental Association, Handoffs, and State Tracking.
    """
    def __init__(self, memory: MemoryAdapter, model_name: str = "gpt-4o"):
        self.memory = memory
        self.pipeline = PipelineExecutor(LLMExecutor(model_name=model_name))
        
        # Core Infrastructures
        self.tool_registry = ToolRegistry()
        
        # Hardcoded static registry for MVP. Future MVP uses Vector/Hypergraph semantic search.
        self.agent_registry = {
            "SystemSeeker": SystemSeeker(model_name="gpt-4o-mini"),
            "QASeeker": QASeeker(model_name="gpt-4o-mini"),
            "DevOpsSeeker": DevOpsSeeker(model_name="gpt-4o-mini"),
            "ResearchSeeker": ResearchSeeker(model_name="gpt-4o-mini"),
            "CodingSeeker": CodingSeeker(model_name="gpt-4o-mini"),
            "ArchitectureEstimator": ArchitectureEstimator(model_name="gpt-4o"),
            "ActionSeeker": ActionSeeker(tool_registry=self.tool_registry, model_name="gpt-4o"),
            "ProcessAnalyzer": ProcessAnalyzer(memory_adapter=self.memory, model_name="gpt-4o"),
            "StrategyGrader": StrategyGrader(model_name="gpt-4o"),
            "OptimizationSeeker": OptimizationSeeker(memory_adapter=self.memory, model_name="gpt-4o"),
            "InsightInternalizer": InsightInternalizer(model_name="gpt-4o"),
            "InsightCorrelator": InsightCorrelator(memory_adapter=self.memory, model_name="gpt-4o")
        }

        # Initialize the Necessity Sensor (Pre-Frontal Cortex)
        self.necessity_sensor = NecessitySensor(
            tool_registry=self.tool_registry, 
            available_agents=list(self.agent_registry.keys()), 
            model_name="gpt-4o"
        )
        
        # Meta-Cognitive Engines
        self.standardizer = ConceptStandardizer()
        self.experiential_engine = ExperientialLearningModule(self.memory)
        self.knowledge_indexer = KnowledgeIndexer(self.memory)
        
        # Mental Association (Vector Semantic Mapping)
        self.association_faculty = MentalAssociationFaculty()
        
        # Durable Execution Queue
        self.event_bus = DurableEventBus(self.memory)

    def determine_next_step(self, overall_objective: str, environment_state: Any) -> OperatorPlanSchema:
        """
        Dynamic Planning Engine: evaluates the current state and uses Mental Association 
        to decide the next agent to call.
        """
        # Phase 1: Semantic Mapping
        available_nodes = list(self.agent_registry.keys())
        predicted_agent = self.association_faculty.associate_best_agent(overall_objective, available_nodes)
        
        # Phase 2: LLM Strategic Plan Generation
        system_prompt = (
            "You are the Seeking Operator, the central brain of an autonomous swarm.\n"
            "Evaluate the objective and the current state, then decide WHICH sub-agent to call next.\n\n"
            f"AVAILABLE AGENTS:\n{available_nodes}\n\n"
            f"DISPOSABLE TOOLS REGISTERED (Syntax/Knowledge):\n{self.tool_registry.get_all_summaries()}\n\n"
            f"MENTAL ASSOCIATION SUGGESTS: [{predicted_agent}] is the most semantically relevant agent for this task.\n"
            "You may override this suggestion if the State/Ledger dictates a different approach.\n"
            "Respond strictly with the required JSON Schema."
        )
        
        user_prompt = f"OBJECTIVE: {overall_objective}\n\nCURRENT STATE/LEDGER: {environment_state}"
        
        plan: OperatorPlanSchema = self.pipeline.execute_with_validation(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_class=OperatorPlanSchema
        )
        
        return plan

    def orchestrate(self, user_objective: str, max_steps: int = 5) -> Dict[str, Any]:
        """
        The main coordination loop linking tasks and triggering agents.
        """
        logger.info(f"SWARM STARTING. Main Objective: {user_objective}")
        self.memory.save_state("main_objective", user_objective)
        
        # EXPLOITATION PHASE: Check the Knowledge Indexer for proven strategies
        exploitable_strategy = self.knowledge_indexer.exploit_strategy(user_objective)
        if exploitable_strategy:
            logger.info("⚡ Exploiting heavily optimized strategy from Memory!")
            blueprint = {
                "required_tools": exploitable_strategy.required_tools,
                "dependency_graph": exploitable_strategy.winning_dag,
                "knowledge_grade": exploitable_strategy.performance_grade
            }
            self.memory.save_state("active_resource_blueprint", blueprint)
        else:
            # Phase 0: Necessity Sensor pre-computes the Resource Blueprint
            logger.info("Executing Pre-Flight Necessity Scan...")
            
            # Extract raw relevant meta-insights
            raw_historical_insights = self.memory.extract_insights(user_objective)
            
            blueprint_context = "New complex orchestration request."
            
            # CORRELATION SCREENING: Cross-reference insights library for patterns
            all_insights = self.memory.get_all_insights()
            if len(all_insights) >= 2:
                logger.info("🔗 Deliberate Correlation Screening across insights library...")
                correlator = self.agent_registry["InsightCorrelator"]
                library_context = correlator.build_library_context()
                correlation_result = correlator.execute(
                    objective="Screen the full insights library for correlations.",
                    context=f"CURRENT OBJECTIVE:\n{user_objective}\n\nFULL INSIGHTS LIBRARY:\n{library_context}"
                )
                if correlation_result.get("status") == "success":
                    screening_summary = correlation_result.get("result", {}).get("screening_summary", "")
                    if screening_summary:
                        blueprint_context += f"\n\nCORRELATION SCREENING RESULTS:\n{screening_summary}"
            
            # INTERNALIZATION: Filter insights by scope/mood/intent applicability
            if raw_historical_insights and raw_historical_insights != "No specific past insights found.":
                logger.info("Internalizing raw derived insights for context applicability...")
                internalizer = self.agent_registry["InsightInternalizer"]
                internalizer_context = f"CURRENT OBJECTIVE:\n{user_objective}\n\nRAW INSIGHTS FROM MEMORY:\n{raw_historical_insights}"
                internalized_result = internalizer.execute(objective="Evaluate applicability of historical insights.", context=internalizer_context)
                
                if internalized_result.get("status") == "success":
                    final_injection = internalized_result.get("result", {}).get("final_contextual_injection", "")
                    if final_injection:
                        blueprint_context += f"\n\nCONTEXTUAL DIRECTIVES (Mandatory Rules):\n{final_injection}"
            
            blueprint_result = self.necessity_sensor.execute(objective=user_objective, context=blueprint_context)
            
            if blueprint_result.get("status") == "success":
                blueprint = blueprint_result.get("result", {})
                self.memory.save_state("active_resource_blueprint", blueprint)
                logger.info("✅ Resource Blueprint generated. DAG pre-calculated.")
                
                # Identify if NEW resources were proposed
                new_tools = blueprint.get('new_tools_to_create', [])
                new_agents = blueprint.get('new_agents_to_create', [])
                
                if new_tools:
                    logger.warning(f"Necessity Sensor has mandated the creation of NEW tools/scripts: {new_tools}")
                    logger.info(f"Reasoning: {blueprint.get('creation_reasoning', 'None provided.')}")
                if new_agents:
                    logger.warning(f"Necessity Sensor has mandated the creation of NEW agents: {new_agents}")
                
            else:
                logger.warning("Necessity Sensor failed to generate blueprint. Falling back to dynamic greedy association.")
                self.memory.save_state("active_resource_blueprint", None)
            
        step_count = 0
        while step_count < max_steps:
            # 1. Evaluate State & Plan
            current_state = self.memory.get_execution_history()
            plan = self.determine_next_step(user_objective, current_state)
            
            logger.info(f"Operator selected {plan.selected_agent}: {plan.reasoning}")
            
            if plan.selected_agent not in self.agent_registry:
                logger.error(f"Agent {plan.selected_agent} not found.")
                break
                
            # 2. Enqueue the task into the Durable Event Bus
            task_id = self.event_bus.enqueue_task(
                objective=plan.sub_objective,
                target_agent=plan.selected_agent
            )
            
            # 3. Instantiate and Delegate
            target_agent = self.agent_registry[plan.selected_agent]
            logger.info(f"Delegating to {plan.selected_agent} for execution. Task ID: {task_id}")
            
            # 4. Execute Node (with underlying FSM and Hypothesis Engine)
            result = target_agent.execute(objective=plan.sub_objective, context=str(current_state))
            
            # 5. Log Execution ensuring immutable trace
            self.memory.log_execution(
                caller="Operator",
                target=plan.selected_agent,
                input_data=plan.sub_objective,
                result=result
            )
            
            # Standardize output to map against chaos/Immunity Threats
            standardized = self.standardizer.standardize(str(result))
            
            # 6. Check FSM Completion Status
            if result.get("fsm_state") == "COMPLETED" or result.get("status") == "success":
                self.event_bus.complete_task(task_id)
                # Evaluate if this should be extracted into a reusable Process IP
                if step_count > 0:
                    self.experiential_engine.internalize_successful_sequence(f"Sequence For: {user_objective[:20]}", user_objective)
                    
                return {"status": "completed", "final_state": self.memory.get_execution_history()}
                
            step_count += 1
            
        return {"status": "halted_max_steps", "state": self.memory.get_execution_history()}
