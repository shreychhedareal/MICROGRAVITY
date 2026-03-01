import os

loop_path = r'C:\Users\HP\nanobot\nanobot\agent\loop.py'
with open(loop_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add import for UIAgentExecutorTool
import_block = '        from nanobot.agent.tools.ui_planner import UIUXPlannerTool'
new_import = import_block + '\n        from nanobot.agent.tools.ui_executor import UIAgentExecutorTool'

if import_block in content and 'from nanobot.agent.tools.ui_executor' not in content:
    content = content.replace(import_block, new_import)
    print('Added UIAgentExecutorTool import')

# 2. Register the tool
register_block = '        self.tools.register(UIUXPlannerTool(provider=self.provider, agent_loop=self))'
new_register = register_block + '\n        self.tools.register(UIAgentExecutorTool(workspace=self.workspace))'

if register_block in content and 'UIAgentExecutorTool(' not in content:
    content = content.replace(register_block, new_register)
    print('Registered UIAgentExecutorTool')

with open(loop_path, 'w', encoding='utf-8') as f:
    f.write(content)
