import asyncio
import os
from pathlib import Path

from nanobot.config.loader import load_config
from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.session.manager import SessionManager

async def test_gateway_ui_orchestration():
    print("Testing Gateway + Advanced Visual Browser UI Orchestration...")
    
    config = load_config()
    bus = MessageBus()
    session_manager = SessionManager(config.workspace_path)
    
    # Minimal config to spin up the Gateway's loop component
    model = config.agents.defaults.model
    p = config.get_provider(model)
    provider = LiteLLMProvider(
        api_key=p.api_key if p else None,
        api_base=config.get_api_base(model),
        default_model=model,
    )
    
    # Initialize AgentLoop just like the Gateway does
    # This automatically registers `BrowserTool` and `UIUXPlannerTool`
    agent = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=config.workspace_path,
        model=config.agents.defaults.model,
        temperature=0.3,
        session_manager=session_manager
    )
    
    print("\nSending objective: 'Go to example.com, take a screenshot, figure out the exact coordinates of the header 'Example Domain', and click it using the browser tool.'")
    prompt = "Use the browser tool to navigate to 'https://example.com'. Then, use the UIUXPlanner tool to orchestrate exactly how to click the main header 'Example Domain'. Since UIUXPlanner accepts a screenshot, first use the browser get_html action to grab a screenshot. Then feed the HTML and screenshot to the orchestrator to get the coordinates. Finally, use the browser tool to click exactly those coordinates. Output your final thoughts when done."
    
    # Ask the agent to execute
    response = await agent.process_direct(
        prompt,
        session_key="test-integration",
        channel="cli",
        chat_id="test"
    )
    
    print("\n[Final Response from Agent]")
    print(response)
    
    await agent.close_mcp()

if __name__ == "__main__":
    asyncio.run(test_gateway_ui_orchestration())
