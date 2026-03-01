import asyncio
import os
from pathlib import Path

from nanobot.config.loader import load_config
from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.bus.queue import MessageBus
from nanobot.agent.subagent import SubagentManager
from nanobot.agent.tools.swarm import SpawnSubagentTool

async def main():
    print("Testing UI Executor Handoff Integration...")
    
    # Load default swarm config
    config = load_config()
    model = config.agents.defaults.model
    p = config.get_provider(model)
    
    provider = LiteLLMProvider(
        api_key=p.api_key if p else None,
        api_base=config.get_api_base(model),
        default_model=model,
    )
    
    bus = MessageBus()
    workspace = Path.cwd()
    
    manager = SubagentManager(
        provider=provider,
        workspace=workspace,
        bus=bus
    )
    
    spawn_tool = SpawnSubagentTool(manager=manager, origin_channel="cli", origin_chat_id="direct")
    
    # We ask the swarm to execute a complex physical task.
    # The Subagent should realize it needs the "ui_executor" tool.
    print("\n--- Spawning UI Task Subagent ---")
    await spawn_tool.execute(
        task="Open the Telegram Web app on my desktop. Ensure it is focused, and wait until it is ready."
    )
    
    print("\n--- Waiting for Subagent to dispatch to UI_Agent ---")
    
    # Just sleep and poll the message bus for the final subagent report
    while manager.get_running_count() > 0:
        await asyncio.sleep(1)
        
    print("\n[+] Test complete. Subagents finished.")

if __name__ == "__main__":
    asyncio.run(main())
