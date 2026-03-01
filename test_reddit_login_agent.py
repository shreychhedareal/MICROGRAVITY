import asyncio
import os
from pathlib import Path
from nanobot.agent.subagent import SubagentManager
from nanobot.providers.openai_provider import OpenAIProvider
from nanobot.bus.queue import MessageBus

# Load environment configuration, assuming openai provider is configured correctly.
# If config fails, replace with the mocked provider logic from test_prompt_injection.
with open("c:/Users/HP/nanobot/.nanobot/config.json", "r") as f:
    import json
    config = json.load(f)

async def run_reddit_test():
    workspace = Path("c:/Users/HP/nanobot/workspace")
    bus = MessageBus()
    
    # Needs a real API provider for this test to actually execute tool cycles
    try:
        provider = OpenAIProvider(api_key=config.get("llm", {}).get("openaiApiKey", os.getenv("OPENAI_API_KEY", "")))
        if not provider.api_key:
             print("No OPENAI_API_KEY found. Agent cannot execute tools.")
             return
    except Exception as e:
        print(f"Failed to initialize provider: {e}")
        return
    
    manager = SubagentManager(provider=provider, workspace=workspace, bus=bus)

    task_instruction = (
        "Log in to Reddit using the username 'Sea-Rate-8973' and password 'Ar@151203'. "
        "Navigate to https://www.reddit.com/login, enter the credentials, click the login button, "
        "and take a screenshot named 'reddit_logged_in.png' to confirm success."
    )

    print("Spawning subagent to test Reddit login...")
    result = await manager.spawn(task=task_instruction, label="Reddit Login Test")
    print(result)

    # Note: the subagent runs in the background within the manager's tasks. 
    # For a quick CLI mock like this, we'll wait for tasks to finish.
    while manager.get_running_count() > 0:
        await asyncio.sleep(1)
        
    print("Test finished.")

if __name__ == "__main__":
    asyncio.run(run_reddit_test())
