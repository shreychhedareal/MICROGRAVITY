import asyncio
from pathlib import Path
from nanobot.agent.memory import MemoryStore
from nanobot.agent.tools.memory_tools import SearchHistoryTool, UpdateMemoryTool, ReadMemoryTool

async def test_memory():
    workspace = Path("test_workspace")
    workspace.mkdir(exist_ok=True)
    
    # Instance of store directly
    store = MemoryStore(workspace)
    
    # Write some history
    store.append_history("User prefers dark mode.")
    store.append_history("User likes python.")
    
    # Test SearchHistoryTool
    search_tool = SearchHistoryTool(workspace)
    print("Search 'python':", await search_tool.execute("python"))
    print("Search 'java':", await search_tool.execute("java"))
    
    # Test Update/Read long term memory
    update_tool = UpdateMemoryTool(workspace)
    read_tool = ReadMemoryTool(workspace)
    
    await update_tool.execute("# Important Info\nUser is testing LMDB.")
    print("Read Memory:", await read_tool.execute())
    
    print("SUCCESS")

if __name__ == "__main__":
    asyncio.run(test_memory())
