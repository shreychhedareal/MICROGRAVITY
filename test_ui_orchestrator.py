import asyncio
import os
from pathlib import Path

from nanobot.config.loader import load_config
from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.agent.ui_ux import UIUXAnalyzer
from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus

async def main():
    print("Testing Advanced UI/UX Orchestrator...")
    
    config = load_config()
    model = config.agents.defaults.model
    p = config.get_provider(model)
    
    provider = LiteLLMProvider(
        api_key=p.api_key if p else None,
        api_base=config.get_api_base(model),
        default_model=model,
    )
    
    analyzer = UIUXAnalyzer(provider=provider)
    
    # Fake DOM for a login page
    fake_dom = """
    <html>
      <body>
        <div id="login-container">
          <h2>Welcome Back</h2>
          <input type="text" id="username" placeholder="Enter username" />
          <input type="password" id="password" placeholder="Enter password" />
          <button id="submit-btn" class="primary-btn">Log In</button>
        </div>
      </body>
    </html>
    """
    
    print("\n--- 1. Testing Utility Prediction ---")
    utility = await analyzer.predict_software_utility(fake_dom)
    print(utility)
    
    print("\n--- 2. Testing Interaction Planning ---")
    goal = "Log into the application with username 'admin' and password 'secret123'"
    plan = await analyzer.generate_interaction_plan(goal, fake_dom)
    print(plan)
    
    print("\n--- 3. Testing Continuous Orchestration ---")
    swarm_status = "Subagent 'login_helper' is currently executing 'Submit login form'."
    task_tree = "- [ ] Log into the application\n- [ ] Scrape dashboard"
    eval_result = await analyzer.continuous_orchestration_plan(goal, fake_dom, swarm_status, task_tree)
    print(eval_result)

if __name__ == "__main__":
    asyncio.run(main())
