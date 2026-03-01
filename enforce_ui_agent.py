import os

workspace_path = r'C:\Users\HP\.nanobot\workspace'

# 1. Patch AGENTS.md
agents_path = os.path.join(workspace_path, 'AGENTS.md')
if os.path.exists(agents_path):
    with open(agents_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove desktop_vision and pyautogui mentions
    lines = content.split('\n')
    cleaned = []
    for line in lines:
        if any(term in line.lower() for term in ['desktop_vision', 'pyautogui']):
            continue
        cleaned.append(line)
    
    with open(agents_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(cleaned))
    print('Cleaned AGENTS.md')

# 2. Patch SOUL.md
soul_path = os.path.join(workspace_path, 'SOUL.md')
if os.path.exists(soul_path):
    with open(soul_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '## UI Automation Directive (RESTRICTED)' not in content:
        directive = '''
## UI Automation Directive (RESTRICTED)
- You are strictly FORBIDDEN from using pyautogui, pynput, or any direct coordinate-based coordinate scripting via exec.
- You are strictly FORBIDDEN from attempting to build or use "desktop vision" tools.
- For ALL UI automation, desktop navigation, and GUI interaction, you MUST exclusively use the ui_planner and ui_executor tools. This is a non-negotiable architectural constraint.
'''
        content += directive
        with open(soul_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print('Updated SOUL.md with UI Agent restriction')

# 3. Patch PROFILE.md
profile_path = os.path.join(workspace_path, 'memory', 'PROFILE.md')
if os.path.exists(profile_path):
    with open(profile_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    preference = '''
- The user has a non-negotiable preference for the AntiGravity UI Agent Engine.
- Never suggest or use pyautogui or standalone vision scripts.
- Only the ui_planner and ui_executor tools are sanctioned for UI work.
'''
    if preference not in content:
        content += preference
        with open(profile_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print('Updated PROFILE.md with user preference')

# 4. Remove test files and scratch files
files_to_delete = [
    r'C:\Users\HP\nanobot\test_live_vision.py',
    r'C:\Users\HP\nanobot\test_trace2.txt'
]
for f in files_to_delete:
    if os.path.exists(f):
        os.remove(f)
        print(f'Deleted {f}')
