import os

workspace_path = r'C:\Users\HP\.nanobot\workspace'

def sanitize_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace specific terms with generic ones
        content = content.replace('pyautogui', 'custom GUI scripts')
        content = content.replace('PyAutoGUI', 'custom GUI scripts')
        content = content.replace('pynput', 'custom input scripts')
        content = content.replace('desktop_vision', 'standalone vision tools')
        content = content.replace('DesktopVisionTool', 'standalone vision tools')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Sanitized {file_path}')

# Sanitize identity and preference files
sanitize_file(os.path.join(workspace_path, 'SOUL.md'))
sanitize_file(os.path.join(workspace_path, 'memory', 'PROFILE.md'))
sanitize_file(os.path.join(workspace_path, 'memory', 'EXPERIENCE_LEDGER.md'))
sanitize_file(os.path.join(workspace_path, 'AGENTS.md'))

# Double check if any other files in memory have these terms
memory_dir = os.path.join(workspace_path, 'memory')
for f in os.listdir(memory_dir):
    if f.endswith('.md') or f.endswith('.json'):
        sanitize_file(os.path.join(memory_dir, f))

# Remove the specific scratch script I wrote earlier
scripts_to_remove = [
    os.path.join(workspace_path, 'type_notepad.py'),
    os.path.join(workspace_path, 'open_calculator.py') # Just in case
]
for p in scripts_to_remove:
    if os.path.exists(p):
        os.remove(p)
        print(f'Removed scratch script: {p}')
