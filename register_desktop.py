import os

loop_path = r'C:\Users\HP\nanobot\nanobot\agent\loop.py'
with open(loop_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add import for DesktopVisionTool
import_block = '        from nanobot.agent.tools.ui_executor import UIAgentExecutorTool'
new_import = import_block + '\n        from nanobot.agent.tools.desktop import DesktopVisionTool'

if import_block in content and 'from nanobot.agent.tools.desktop' not in content:
    content = content.replace(import_block, new_import)
    print('Added DesktopVisionTool import')

# 2. Register the tool
register_block = '        self.tools.register(UIAgentExecutorTool(workspace=self.workspace))'
new_register = register_block + '\n        self.tools.register(DesktopVisionTool(workspace=self.workspace))'

if register_block in content and 'DesktopVisionTool(' not in content:
    content = content.replace(register_block, new_register)
    print('Registered DesktopVisionTool')

with open(loop_path, 'w', encoding='utf-8') as f:
    f.write(content)
