"""Integration test for all 7 processor modules."""
import shutil
from pathlib import Path


def test_processors():
    workspace = Path("test_processors_ws")
    if workspace.exists():
        shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir()

    from nanobot.agent.processors.cache import IntelligentCache
    from nanobot.agent.processors.bulk_io import BulkIOProcessor
    from nanobot.agent.processors.speculative_planner import SpeculativePlanner
    from nanobot.agent.processors.routing import RoutingMapper
    from nanobot.agent.processors.learner import IncrementalLearner
    from nanobot.agent.processors.awareness import AwarenessProjector
    from nanobot.agent.processors.arch_knowledge import ArchitectureKnowledgeBase

    print("=" * 55)
    print("PROCESSOR MODULES INTEGRATION TEST")
    print("=" * 55)

    # ── 1. Intelligent Cache ──────────────────────────────────────
    print("\n--- Test 1: Intelligent Cache ---")
    cache = IntelligentCache(max_size=10, default_ttl=60)
    assert cache.get("hello world") is None, "FAIL: should miss"
    cache.put("hello world", "greeting response")
    hit = cache.get("hello world")
    assert hit == "greeting response", "FAIL: cache should hit"
    stats = cache.get_stats()
    assert stats["hits_exact"] == 1, "FAIL: exact hit count"
    print(f"  Stats: {stats}")
    print("  OK")

    # ── 2. Bulk I/O ───────────────────────────────────────────────
    print("\n--- Test 2: Bulk I/O Processor ---")
    flushed_batches = []
    bio = BulkIOProcessor(workspace, flush_callback=lambda batch: flushed_batches.append(batch), max_buffer=3)
    bio.enqueue_write({"text": "entry1"})
    bio.enqueue_write({"text": "entry2"})
    assert len(flushed_batches) == 0, "FAIL: should not flush yet"
    bio.enqueue_write({"text": "entry3"})  # triggers flush at 3
    assert len(flushed_batches) == 1, "FAIL: should auto-flush at max_buffer"
    assert len(flushed_batches[0]) == 3, "FAIL: batch should have 3 entries"
    print(f"  Stats: {bio.get_stats()}")
    print("  OK")

    # ── 3. Speculative Planner ────────────────────────────────────
    print("\n--- Test 3: Speculative Planner ---")
    sp = SpeculativePlanner(workspace, confidence_threshold=0.5)
    # Simulate tool sequence: read_file → exec_shell → read_file → exec_shell
    sp.on_tool_called("read_file")
    sp.on_tool_called("exec_shell")
    sp.on_tool_called("read_file")
    sp.on_tool_called("exec_shell")
    sp.on_tool_called("read_file")
    preds = sp.on_tool_called("exec_shell")  # after exec_shell, should predict read_file
    sp.on_tool_called("read_file")  # validates prediction
    stats = sp.get_stats()
    print(f"  Predictions: {stats['predictions_made']}, Correct: {stats['predictions_correct']}")
    print(f"  Accuracy: {stats['accuracy']:.0%}")
    assert stats["predictions_made"] > 0, "FAIL: should have made predictions"
    print("  OK")

    # ── 4. Routing Mapper ─────────────────────────────────────────
    print("\n--- Test 4: Routing Mapper ---")
    router = RoutingMapper(workspace, auto_dispatch_threshold=0.6)
    route = router.add_route("search the web", "web_search", "tool")
    route.record_use(True)
    route.record_use(True)
    route.record_use(True)
    matches = router.find_routes("search the web for python docs")
    assert len(matches) > 0, "FAIL: should match"
    assert matches[0]["route"].target == "web_search"
    auto = router.should_auto_dispatch("search the web for latest news")
    assert auto is not None, "FAIL: should auto-dispatch"
    print(f"  Auto-dispatch: {auto.target} (success: {auto.success_rate:.0%})")
    print("  OK")

    # ── 5. Incremental Learner ────────────────────────────────────
    print("\n--- Test 5: Incremental Learner ---")
    learner = IncrementalLearner(workspace)
    learner.record_tool_use("web_search", True, latency_ms=500)
    learner.record_tool_use("web_search", True, latency_ms=300)
    learner.record_tool_use("exec_shell", False, latency_ms=1200)
    learner.record_tool_use("exec_shell", False, latency_ms=800)
    learner.record_tool_use("exec_shell", True, latency_ms=400)
    learner.record_skill_use("code_generation", "github")
    learner.record_agent_strategy("research", "researcher", True)
    learner.record_agent_strategy("research", "worker", False)
    insights = learner.get_tool_insights()
    failing = learner.get_failing_tools(threshold=0.5)
    best_persona = learner.best_persona_for_task("research")
    print(f"  Tools tracked: {len(insights)}")
    print(f"  Failing tools: {[f['name'] for f in failing]}")
    print(f"  Best persona for research: {best_persona}")
    assert best_persona == "researcher", "FAIL: researcher should be best"
    print("  OK")

    # ── 6. Awareness Projector ────────────────────────────────────
    print("\n--- Test 6: Awareness Projector ---")
    awareness = AwarenessProjector(workspace)
    awareness.self_model.update(tools=["web_search", "exec_shell"], skills=["github", "cron"])
    sa = awareness.register_subagent("SA-001", "Research Python docs", "researcher")
    sa.update_progress(40.0, remaining_s=30)
    sa.request_from_controller("Need API key for Python docs")
    snapshot = awareness.generate_snapshot()
    assert snapshot["swarm_health"] == "degraded", "FAIL: blocked agent should degrade health"
    pending = awareness.get_pending_requests()
    assert len(pending) == 1, "FAIL: should have 1 pending request"
    context_str = awareness.generate_context_string()
    print(context_str)
    print("  OK")

    # ── 7. Architecture Knowledge Base ────────────────────────────
    print("\n--- Test 7: Architecture Knowledge Base ---")
    arch = ArchitectureKnowledgeBase(workspace)
    explanation = arch.explain("IntelligentCache")
    assert "LRU" in explanation, "FAIL: explanation should mention LRU"
    print(f"  Components: {len(arch._components)}")
    deps = arch.get_dependency_graph()
    critical = arch.get_critical_path()
    print(f"  Critical path: {critical}")
    report = arch.generate_connectionism_report()
    assert "ARCHITECTURE CONNECTIONISM REPORT" in report
    print(f"  Report length: {len(report)} chars")
    print("  OK")

    # Cleanup
    shutil.rmtree(workspace, ignore_errors=True)

    print("\n" + "=" * 55)
    print("ALL PROCESSOR TESTS PASSED")
    print("=" * 55)


if __name__ == "__main__":
    test_processors()
