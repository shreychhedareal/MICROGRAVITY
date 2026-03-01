import os

# Files to clean
targets = [
    r'C:\Users\HP\.nanobot\workspace\SYSTEM_CATALOG.md',
    r'C:\Users\HP\nanobot\workspace\SYSTEM_CATALOG.md',
    r'C:\Users\HP\nanobot\SYSTEM_CATALOG.md'
]

for target in targets:
    if os.path.exists(target):
        with open(target, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Filter out Brave/web_search lines
        cleaned = [line for line in lines if 'web_search' not in line.lower() and 'brave' not in line.lower()]
        
        with open(target, 'w', encoding='utf-8') as f:
            f.writelines(cleaned)
        print(f'Cleaned {target}')
    else:
        print(f'Skipped {target} (not found)')

# Also patch loop.py to disable WebSearchTool registration
loop_path = r'C:\Users\HP\nanobot\nanobot\agent\loop.py'
if os.path.exists(loop_path):
    with open(loop_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Comment out the registration
    content = content.replace(
        'self.tools.register(WebSearchTool(api_key=self.brave_api_key))',
        '# self.tools.register(WebSearchTool(api_key=self.brave_api_key))'
    )
    
    with open(loop_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Disabled WebSearchTool in loop.py')
