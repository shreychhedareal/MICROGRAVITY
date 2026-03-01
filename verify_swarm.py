"""Integration test for swarm architecture: TaskTree, Scheduler, Consequence Storage."""
import asyncio
import shutil
from pathlib import Path


async def test_swarm_architecture():
    workspace = Path("test_swarm_ws")
    if workspace.exists():
        shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir()

    from nanobot.agent.task_tree import TaskTree
    from nanobot.agent.scheduler import Scheduler
    from nanobot.agent.memory import MemoryStore

    tree = TaskTree(workspace)
    scheduler = Scheduler(workspace)
    store = MemoryStore(workspace)

    print("=" * 50)
    print("SWARM ARCHITECTURE INTEGRATION TEST")
    print("=" * 50)

    # ── Phase 1: Task Tree DAG ────────────────────────────────────
    print("\n--- Test 1: Task Tree Creation ---")
    t1 = tree.add_task("Design API schema", priority="high", labels=["api", "backend"])
    t2 = tree.add_task("Implement endpoints", depends_on=[t1.id], labels=["api", "backend"])
    t3 = tree.add_task("Write tests", depends_on=[t2.id], labels=["testing"])
    print(f"  Created: {t1.id}, {t2.id}, {t3.id}")
    assert len(tree.get_all_tasks()) == 3, "FAIL: Expected 3 tasks"
    print("  OK")

    print("\n--- Test 2: Dependency Blocking ---")
    err = tree.start_task(t2.id)
    assert err is not None, "FAIL: t2 should be blocked by t1"
    print(f"  Correctly blocked: {err}")

    ready = tree.get_ready_tasks()
    assert len(ready) == 1 and ready[0].id == t1.id, "FAIL: Only t1 should be ready"
    print(f"  Ready tasks: {[t.title for t in ready]}")
    print("  OK")

    print("\n--- Test 3: Task Progress ---")
    tree.start_task(t1.id)
    tree.checkpoint(t1.id, "Schema draft v1 complete")
    tree.complete_task(t1.id, consequence="REST API uses OpenAPI 3.1 with JWT auth")
    
    ready = tree.get_ready_tasks()
    assert len(ready) == 1 and ready[0].id == t2.id, "FAIL: t2 should now be ready"
    print(f"  After t1 complete, ready: {[t.title for t in ready]}")
    print("  OK")

    print("\n--- Test 4: Tree Rendering ---")
    rendered = tree.render_tree()
    print(rendered)
    assert "Design API schema" in rendered, "FAIL: Render should contain task title"
    print("  OK")

    # ── Phase 2: Consequence Storage ──────────────────────────────
    print("\n--- Test 5: Consequence Storage & Recall ---")
    store.store_consequence(
        "REST API uses OpenAPI 3.1 with JWT auth. Rate limit: 100/min.",
        domain_labels=["api", "auth"]
    )
    store.store_consequence(
        "Database uses PostgreSQL 15 with connection pooling via pgbouncer.",
        domain_labels=["database", "infra"]
    )

    results = store.recall_consequences("JWT auth rate limit", domain_labels=["api"])
    print(f"  Recalled {len(results)} consequences for 'JWT auth rate limit' + api label")
    for r in results:
        print(f"    -> {r[:80]}")
    assert len(results) > 0, "FAIL: Should recall at least one consequence"
    print("  OK")

    # ── Phase 3: Vector Label Discovery ───────────────────────────
    print("\n--- Test 6: Label Discovery ---")
    labels = store.vector.list_labels()
    print(f"  All labels in store: {labels}")
    assert "consequence" in labels, "FAIL: 'consequence' label should exist"
    assert "api" in labels, "FAIL: 'api' label should exist"
    print("  OK")

    # ── Phase 4: Scheduler Triggers ───────────────────────────────
    print("\n--- Test 7: Event Trigger ---")
    fired_actions = []

    async def on_action(action):
        fired_actions.append(action)

    scheduler.on_action(on_action)
    scheduler.register_event_trigger(
        name="Critical Error Alert",
        watch_labels=["error", "critical"],
        action_description="Send alert to admin channel"
    )

    actions = await scheduler.on_data_stored(
        labels=["error", "critical"],
        text="NullPointerException in payment service"
    )
    assert len(actions) == 1, "FAIL: Event trigger should have fired"
    assert len(fired_actions) == 1, "FAIL: Callback should have been invoked"
    print(f"  Trigger fired: {actions[0].description}")
    print("  OK")

    print("\n--- Test 8: Consequence Trigger ---")
    scheduler.register_consequence_trigger(
        name="Deploy After Tests Pass",
        watch_keywords=["tests pass", "all tests"],
        action_description="Trigger deployment pipeline"
    )

    actions = await scheduler.on_task_completed("All tests pass for the API module.")
    assert len(actions) == 1, "FAIL: Consequence trigger should have fired"
    print(f"  Trigger fired: {actions[0].description}")
    print("  OK")

    print("\n--- Test 9: Scheduler Status ---")
    print(scheduler.render_status())

    # ── Phase 5: Process Templates ────────────────────────────────
    print("\n--- Test 10: Process Template Extraction ---")
    template = tree.extract_template([t1.id, t2.id, t3.id])
    assert len(template["steps"]) == 3, "FAIL: Template should have 3 steps"
    print(f"  Extracted template with {len(template['steps'])} steps")
    
    new_tasks = tree.instantiate_template(template, title_prefix="[v2] ")
    assert len(new_tasks) == 3, "FAIL: Should instantiate 3 new tasks"
    print(f"  Instantiated: {[t.title for t in new_tasks]}")
    print("  OK")

    # Cleanup
    shutil.rmtree(workspace, ignore_errors=True)

    print("\n" + "=" * 50)
    print("ALL SWARM ARCHITECTURE TESTS PASSED")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_swarm_architecture())
