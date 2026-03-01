import re

intent_path = r'C:\Users\HP\nanobot\nanobot\agent\intent.py'
with open(intent_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add a clear instruction at the end of the prompt telling
# the LLM to NEVER halt when the user explicitly names a tool
old_block = '''            If the task requires visual browser inspection, set 'proceed_immediately' to TRUE, because the Swarm has the rowser tool specifically for this. If it's just writing code, editing files, or talking, also set it to TRUE (unless you are pausing to confirm a speculative larger vision).'''

new_block = '''            If the task requires visual browser inspection, set 'proceed_immediately' to TRUE, because the Swarm has the rowser tool specifically for this. If it's just writing code, editing files, or talking, also set it to TRUE (unless you are pausing to confirm a speculative larger vision).

            CRITICAL OVERRIDE: If the user EXPLICITLY names a specific tool they want to use (e.g. "use ui_executor", "use the browser tool", "use exec"), you MUST set 'proceed_immediately' to TRUE and 'is_capability_expansion' to FALSE. The user has made a deliberate, informed tool choice — do NOT second-guess it or halt to ask if they are "testing". Execute their request directly.'''

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(intent_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Patched intent.py prompt with CRITICAL OVERRIDE for explicit tool requests')
else:
    print('Target block not found in intent.py')
