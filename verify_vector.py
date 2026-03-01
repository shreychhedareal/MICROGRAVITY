"""Verify vector search integration."""
import asyncio
import os
import shutil
from pathlib import Path

async def _run_test_suite(name: str, conceptual: bool = False):
    workspace = Path("test_vector_ws")
    if workspace.exists():
        shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir()

    # Import inside after env config
    from nanobot.agent.memory import MemoryStore
    from nanobot.agent.tools.memory_tools import SemanticSearchTool

    store = MemoryStore(workspace)
    
    print(f"\n{'='*50}\nRUNNING SUITE: {name}\n{'='*50}")
    print(f"Embedder selected: {type(store.vector._embedder).__name__}")

    # Add diverse history entries
    store.append_history("[2026-02-27] User asked about Python performance tuning and profiling tools.", labels=["python", "backend"])
    store.append_history("[2026-02-26] Discussed database migration strategies for PostgreSQL.", labels=["database", "backend"])
    store.append_history("[2026-02-25] Implemented a new REST API endpoint for user authentication.", labels=["api", "backend"])
    store.append_history("[2026-02-24] Debugged memory leak in the background task scheduler.", labels=["python", "backend"])
    store.append_history("[2026-02-23] User prefers dark mode and uses VS Code as their editor.", labels=["preferences", "frontend"])

    # Add long-term memory
    store.write_long_term(
        "## User Preferences\nThe user prefers dark mode interfaces.\nThey use VS Code.\n\n"
        "## Project Context\nThe project uses FastAPI with PostgreSQL.\nAuth is handled via OAuth2.\n\n"
        "## Technical Notes\nAlways use connection pooling for database access.\nRun profiling before optimizing.",
        labels=["project", "settings"]
    )

    if conceptual:
        print("\n=== Test 1 (Conceptual): Search history for 'speed optimization' ===")
        results = store.semantic_search_history("speed optimization", n_results=3)
    else:
        print("\n=== Test 1 (Literal): Search history for 'performance profiling' ===")
        results = store.semantic_search_history("performance profiling", n_results=3)
        
    for r in results:
        print(f"  -> {r[:80]}")
    assert len(results) > 0, "FAIL: No results returned"

    if conceptual:
        print("\n=== Test 2 (Conceptual): Search history for 'login system' ===")
        results = store.semantic_search_history("login system", n_results=3)
    else:
        print("\n=== Test 2 (Literal): Search history for 'user authentication' ===")
        results = store.semantic_search_history("user authentication", n_results=3)
        
    for r in results:
        print(f"  -> {r[:80]}")
    assert len(results) > 0, "FAIL: No results returned"

    if conceptual:
        print("\n=== Test 3 (Conceptual): Search memory for 'database best practices' ===")
        results = store.semantic_search_memory("database best practices", n_results=3)
    else:
        print("\n=== Test 3 (Literal): Search memory for 'database PostgreSQL' ===")
        results = store.semantic_search_memory("database PostgreSQL", n_results=3)
        
    for r in results:
        print(f"  -> {r[:80]}")
    assert len(results) > 0, "FAIL: No results returned"

    print("\n=== Test 4: SemanticSearchTool tool call ===")
    tool = SemanticSearchTool(workspace)
    query = "editor settings" if conceptual else "VS Code editor"
    result = await tool.execute(query=query, collection="memory", n_results=3)
    print(f"  -> {result[:120]}")
    assert "No semantically similar" not in result, "FAIL: No results from tool"
    print("  OK")

    print("\n=== Test 5: Categorical Cluster Filtering ===")
    results_frontend = store.semantic_search_history("dark mode editor", n_results=3, labels=["frontend"])
    print("Frontend cluster matches (should be only preferences):")
    for r in results_frontend:
        print(f"  -> {r[:80]}")
    assert len(results_frontend) > 0, "Wait, should have matched the VS Code entry"
    assert "prefers dark mode" in results_frontend[0], "FAIL: Label filter leaked or failed"
    print("  OK: Categorical filter applied successfully.")


async def test_vector():
    import os
    # 1. Test Fallback (TF-IDF)
    old_key = os.environ.get("GEMINI_API_KEY")
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]
        
    await _run_test_suite("TF-IDF Fallback", conceptual=False)
    
    # 2. Test Gemini (if key was provided)
    if old_key:
        os.environ["GEMINI_API_KEY"] = old_key
        # We need to force a reload of the embedder since it's cached in the module
        import importlib
        import nanobot.agent.vectorstore
        importlib.reload(nanobot.agent.vectorstore)
        await _run_test_suite("Gemini Embeddings", conceptual=True)
    else:
        print("\nSkipping Gemini tests because GEMINI_API_KEY is not set.")

    print("\nALL TESTS PASSED")

if __name__ == "__main__":
    asyncio.run(test_vector())
