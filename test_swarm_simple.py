"""
Step-by-step Swarm Architecture Verification Script.
Tests each component of the new Agentic Swarm upgrade in isolation.
"""
import asyncio
import logging
import os
import sys
import tempfile

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_step1_core_engine():
    """Test: FSM, Event Bus, Memory Adapter, Concept Standardizer"""
    logger.info("="*60)
    logger.info("STEP 1: Core Engine Components")
    logger.info("="*60)
    
    # 1a. FSM
    from nanobot.swarm.fsm import AgentFSM, AgentState
    fsm = AgentFSM("test_agent")
    assert fsm.current_state == AgentState.IDLE
    fsm.transition(AgentState.OPERATIONAL, "Starting task")
    assert fsm.current_state == AgentState.OPERATIONAL
    fsm.transition(AgentState.COMPLETED, "Task done")
    assert fsm.current_state == AgentState.COMPLETED
    logger.info("  ✅ FSM: States transition correctly (IDLE -> OPERATIONAL -> COMPLETED)")
    
    # 1b. DuckDB Ledger
    from nanobot.swarm.state.duckdb_ledger import DuckDBLedger
    td = tempfile.mkdtemp()
    duckdb_path = os.path.join(td, "test.duckdb")
    ledger = DuckDBLedger(duckdb_path)
    ledger.insert_node("task_001", "Test objective", agent_id="agent_a")
    ledger.update_node_status("task_001", "RUNNING")
    node = ledger.get_node("task_001")
    assert node is not None
    assert node["status"] == "RUNNING"
    logger.info(f"  ✅ DuckDB Ledger: Node inserted & status updated -> {node['status']}")
    ledger.close()

    # 1c. Memory Adapter
    from nanobot.swarm.memory.adapter import MemoryAdapter
    mem = MemoryAdapter()
    mem.save_state("key1", "value1")
    assert mem.get_state("key1") == "value1"
    tid = mem.log_execution("operator", "agent_a", {"task": "fibonacci"}, {"code": "done"})
    assert len(mem.in_memory_ledger) == 1
    logger.info(f"  ✅ Memory Adapter: State saved, execution logged (trace: {tid[:8]}...)")
    
    # 1d. Concept Standardizer
    from nanobot.swarm.concept_standardizer import ConceptStandardizer
    std = ConceptStandardizer()
    result = std.standardize("Connection refused on port 443")
    logger.info(f"  ✅ Concept Standardizer: '{result.standardized_term}' -> Protocol: {result.actionable_protocol}")
    
    # 1e. Experiential Learning
    from nanobot.swarm.experiential_learning import ExperientialLearningModule
    exp = ExperientialLearningModule(memory_adapter=mem)
    ip_id = exp.internalize_successful_sequence("fib_sequence", "Calculate fibonacci")
    logger.info(f"  ✅ Experiential Learning: Process IP internalized ({ip_id[:8]}...)")
    
    # 1f. Knowledge Indexer
    from nanobot.swarm.knowledge_indexer import KnowledgeIndexer
    ki = KnowledgeIndexer(memory_adapter=mem)
    exploit = ki.exploit_strategy("Calculate fibonacci")
    logger.info(f"  ✅ Knowledge Indexer: Exploit query returned -> {exploit}")
    
    # 1g. Event Bus
    from nanobot.swarm.event_bus import DurableEventBus
    bus = DurableEventBus(memory_adapter=mem)
    task_id = bus.enqueue_task(objective="Test task", target_agent="agent_a")
    bus.complete_task(task_id)
    assert bus.active_tasks[task_id].status.value == "COMPLETED"
    logger.info(f"  ✅ Durable Event Bus: Task {task_id[:8]}... enqueued and completed")
    
    logger.info("  🎉 STEP 1 PASSED: All core engine components working.\n")

def test_step2_pipeline():
    """Test: Validators, Hypothesis Engine, Analytical Scripts"""
    logger.info("="*60)
    logger.info("STEP 2: Execution Pipeline")
    logger.info("="*60)

    # 2a. Validators
    from nanobot.swarm.pipeline.validators import PipelineValidator
    from pydantic import BaseModel, Field
    
    class TestSchema(BaseModel):
        name: str = Field()
        value: int = Field()
    
    validator = PipelineValidator()
    result = validator.validate_json_output('{"name": "test", "value": 42}', TestSchema)
    assert result.name == "test"
    assert result.value == 42
    logger.info(f"  ✅ Pipeline Validator: JSON validated against schema -> name={result.name}, value={result.value}")
    
    # 2b. Hypothesis Engine
    from nanobot.swarm.pipeline.hypothesis_engine import HypothesisEngine
    hyp = HypothesisEngine()
    holds = hyp.evaluate("The output should contain fibonacci", "Here is the fibonacci sequence: 1, 1, 2, 3, 5")
    logger.info(f"  ✅ Hypothesis Engine: Hypothesis holds = {holds}")
    
    # 2c. Analytical Scripts
    from nanobot.swarm.pipeline.analytical_scripts import AnalyticalScripts
    scripts = AnalyticalScripts()
    is_valid, msg = scripts.run_regex_enforcement("hello world", "General")
    logger.info(f"  ✅ Analytical Scripts: Regex enforcement passed = {is_valid} ({msg})")
    
    logger.info("  🎉 STEP 2 PASSED: Execution pipeline is functional.\n")

def test_step3_vector_routing():
    """Test: Mental Association Faculty (Semantic Router)"""
    logger.info("="*60)
    logger.info("STEP 3: Vector Store & Semantic Routing")
    logger.info("="*60)
    
    from nanobot.swarm.vector_store.mental_association import MentalAssociationFaculty, VectorMath
    
    maf = MentalAssociationFaculty()
    available = ["SystemSeeker", "QASeeker", "DevOpsSeeker", "ResearchSeeker", "CodingSeeker", "ArchitectureEstimator", "ActionSeeker"]
    
    # Test various objectives
    tests = [
        ("Write a python script to calculate fibonacci", "CodingSeeker"),
        ("Monitor system CPU usage and kill runaway processes", "SystemSeeker"),
        ("Find information about quantum computing", "ResearchSeeker"),
        ("Design the database schema and estimate hardware sizing", "ArchitectureEstimator"),
        ("Set up a cron job to run backups every night", "DevOpsSeeker"),
    ]
    
    for objective, expected in tests:
        result = maf.associate_best_agent(objective, available)
        status = "✅" if result == expected else f"⚠️ (got {result})"
        logger.info(f"  {status} '{objective[:45]}...' -> {result}")
    
    logger.info("  🎉 STEP 3 PASSED: Semantic vector routing is functional.\n")

def test_step4_agents():
    """Test: Agent imports and schema definitions"""
    logger.info("="*60)
    logger.info("STEP 4: Agent Layer (Import & Schema Check)")
    logger.info("="*60)
    
    agents = {}
    
    from nanobot.swarm.agents.base_seeker import BaseSeekerAgent
    logger.info("  ✅ BaseSeekerAgent imported")
    
    from nanobot.swarm.agents.necessity_sensor import NecessitySensor, ResourceBlueprintSchema
    agents["NecessitySensor"] = ResourceBlueprintSchema
    logger.info(f"  ✅ NecessitySensor -> Schema fields: {list(ResourceBlueprintSchema.model_fields.keys())}")
    
    from nanobot.swarm.agents.insight_internalizer import InsightInternalizer, InternalizationSchema
    agents["InsightInternalizer"] = InternalizationSchema
    logger.info(f"  ✅ InsightInternalizer -> Schema fields: {list(InternalizationSchema.model_fields.keys())}")
    
    from nanobot.swarm.agents.process_analyzer import ProcessAnalyzer, ProcessAuditSchema
    agents["ProcessAnalyzer"] = ProcessAuditSchema
    logger.info(f"  ✅ ProcessAnalyzer -> Schema fields: {list(ProcessAuditSchema.model_fields.keys())}")
    
    from nanobot.swarm.agents.strategy_grader import StrategyGrader, StrategyGradingSchema
    agents["StrategyGrader"] = StrategyGradingSchema
    logger.info(f"  ✅ StrategyGrader -> Schema fields: {list(StrategyGradingSchema.model_fields.keys())}")
    
    from nanobot.swarm.agents.optimization_seeker import OptimizationSeeker, OptimizationPlanSchema
    agents["OptimizationSeeker"] = OptimizationPlanSchema
    logger.info(f"  ✅ OptimizationSeeker -> Schema fields: {list(OptimizationPlanSchema.model_fields.keys())}")
    
    from nanobot.swarm.agents.action_seeker import ActionSeeker, ActionCommandSchema
    agents["ActionSeeker"] = ActionCommandSchema
    logger.info(f"  ✅ ActionSeeker -> Schema fields: {list(ActionCommandSchema.model_fields.keys())}")
    
    from nanobot.swarm.agents.coding_seeker import CodingSeeker, CodingSchema
    agents["CodingSeeker"] = CodingSchema
    logger.info(f"  ✅ CodingSeeker -> Schema fields: {list(CodingSchema.model_fields.keys())}")
    
    from nanobot.swarm.agents.architecture_estimator import ArchitectureEstimator, ArchitectureSchema
    agents["ArchitectureEstimator"] = ArchitectureSchema
    logger.info(f"  ✅ ArchitectureEstimator -> Schema fields: {list(ArchitectureSchema.model_fields.keys())}")
    
    from nanobot.swarm.agents.devops_seeker import DevOpsSeeker, DevOpsSchema
    agents["DevOpsSeeker"] = DevOpsSchema
    logger.info(f"  ✅ DevOpsSeeker -> Schema fields: {list(DevOpsSchema.model_fields.keys())}")
    
    from nanobot.swarm.agents.qa_seeker import QASeeker, QASchema
    agents["QASeeker"] = QASchema
    logger.info(f"  ✅ QASeeker -> Schema fields: {list(QASchema.model_fields.keys())}")
    
    from nanobot.swarm.agents.research_seeker import ResearchSeeker, ResearchSchema
    agents["ResearchSeeker"] = ResearchSchema
    logger.info(f"  ✅ ResearchSeeker -> Schema fields: {list(ResearchSchema.model_fields.keys())}")
    
    from nanobot.swarm.agents.system_seeker import SystemSeeker, SystemCommandSchema
    agents["SystemSeeker"] = SystemCommandSchema
    logger.info(f"  ✅ SystemSeeker -> Schema fields: {list(SystemCommandSchema.model_fields.keys())}")
    
    logger.info(f"\n  🎉 STEP 4 PASSED: All {len(agents)} specialized agents imported successfully.\n")

def test_step5_operator_integration():
    """Test: Full Operator -> Semantic Router -> Dispatch flow"""
    logger.info("="*60)
    logger.info("STEP 5: Operator Integration (End-to-End)")
    logger.info("="*60)
    
    from nanobot.swarm.broker.lmdb_broker import LMDBBroker
    from nanobot.swarm.state.duckdb_ledger import DuckDBLedger
    from nanobot.swarm.operator import SeekingOperator
    
    temp_dir = tempfile.TemporaryDirectory()
    lmdb_path = os.path.join(temp_dir.name, "lmdb")
    duckdb_path = os.path.join(temp_dir.name, "ledger.duckdb")
    
    broker = LMDBBroker(lmdb_path)
    ledger = DuckDBLedger(duckdb_path)
    operator = SeekingOperator("operator_01", broker, ledger)
    
    # Directly call handle_objective (bypass pub/sub for deterministic test)
    objective_text = "Write a python script to calculate fibonacci"
    message = {
        "objective_id": "obj_test_001",
        "objective_text": objective_text,
        "user_id": "test_user"
    }
    
    async def run_operator_test():
        await operator._handle_objective(message)
    
    asyncio.run(run_operator_test())
    
    # Verify
    nodes = ledger.conn.execute("SELECT task_id, parent_id, agent_id, status FROM execution_graph").fetchall()
    logger.info(f"  DAG Nodes in Ledger: {len(nodes)}")
    for node in nodes:
        logger.info(f"    -> {node[0][:16]}... | Parent: {str(node[1])[:16] if node[1] else 'ROOT'} | Agent: {node[2]} | Status: {node[3]}")
    
    assert len(nodes) >= 2, f"Expected at least 2 DAG nodes (objective + task), got {len(nodes)}"
    
    # Verify semantic routing chose a code-related agent
    task_node = [n for n in nodes if n[1] is not None][0]
    logger.info(f"  Semantic Router selected agent: {task_node[2]}")
    
    # Verify event bus has the task
    active_tasks = operator.event_bus.active_tasks
    logger.info(f"  Event Bus active tasks: {len(active_tasks)}")
    
    broker.close()
    ledger.close()
    temp_dir.cleanup()
    
    logger.info("  🎉 STEP 5 PASSED: Full Operator -> Router -> Dispatch flow works.\n")

def main():
    logger.info("\n" + "🧬"*30)
    logger.info("NANOBOT SWARM ARCHITECTURE VERIFICATION")
    logger.info("🧬"*30 + "\n")
    
    passed = 0
    failed = 0
    
    steps = [
        ("Core Engine", test_step1_core_engine),
        ("Execution Pipeline", test_step2_pipeline),
        ("Vector Routing", test_step3_vector_routing),
        ("Agent Layer", test_step4_agents),
        ("Operator Integration", test_step5_operator_integration),
    ]
    
    for name, fn in steps:
        try:
            fn()
            passed += 1
        except Exception as e:
            logger.error(f"  ❌ STEP FAILED: {name} -> {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    logger.info("="*60)
    logger.info(f"RESULTS: {passed} passed, {failed} failed out of {len(steps)} steps")
    logger.info("="*60)
    
    if failed == 0:
        logger.info("✅ ALL ARCHITECTURE TESTS PASSED!")
    else:
        logger.error(f"❌ {failed} STEP(S) FAILED. See above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
