intent_path = r'C:\Users\HP\nanobot\nanobot\agent\intent.py'
with open(intent_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the closing of the prompt (the triple-quote before the try block)
# and inject the CRITICAL OVERRIDE right before it
old_marker = '''        \"\"\")\n        \n        try:'''
new_marker = '''            CRITICAL OVERRIDE: If the user EXPLICITLY names a specific tool they want to use (e.g. "use ui_executor", "use the browser tool", "use exec"), you MUST set 'proceed_immediately' to TRUE and 'is_capability_expansion' to FALSE. The user has made a deliberate, informed tool choice. Do NOT second-guess it, do NOT halt to ask if they are testing. Execute their request directly.
        \"\"\")\n        \n        try:'''

if old_marker in content:
    content = content.replace(old_marker, new_marker, 1)
    with open(intent_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Patched intent.py with CRITICAL OVERRIDE')
else:
    print('FAILED: Could not find exact marker in intent.py')
    # Debug: show what's around the triple-quote
    idx = content.find('\"\"\")')
    if idx != -1:
        print(f'Found triple-quote at index {idx}')
        print(repr(content[idx:idx+50]))
