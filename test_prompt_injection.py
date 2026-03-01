import asyncio
from pathlib import Path
from nanobot.agent.context import ContextBuilder
from nanobot.agent.subagent import SubagentManager
from nanobot.providers.base import LLMProvider

class MockProvider(LLMProvider):
    async def chat(self, messages, tools=None, model=None, temperature=0.7, max_tokens=4096): pass
    def get_default_model(self): return "mock-model"
    def count_tokens(self, text): return len(text)
    @property
    def provider_name(self): return "mock"

async def test_prompts():
    workspace = Path("c:/Users/HP/nanobot/workspace")
    cb = ContextBuilder(workspace)
    sys_prompt = cb.build_system_prompt()
    
    sub = SubagentManager(provider=MockProvider(), workspace=workspace, bus=None)
    sub_prompt = sub._build_subagent_prompt("Test task")
    
    with open("c:/Users/HP/nanobot/prompt_output.txt", "w", encoding="utf-8") as f:
        f.write("=== MAIN AGENT PROMPT ===\n")
        f.write(sys_prompt)
        f.write("\n\n=== SUBAGENT PROMPT ===\n")
        f.write(sub_prompt)
        
if __name__ == "__main__":
    asyncio.run(test_prompts())
