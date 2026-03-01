import json_repair

# --- Patch 1: intent.py ---
intent_path = r'C:\Users\HP\nanobot\nanobot\agent\intent.py'
with open(intent_path, 'r', encoding='utf-8') as f:
    content = f.read()

patched = False

# Add json_repair import if not present
if 'import json_repair' not in content:
    content = content.replace('import json\n', 'import json\nimport json_repair\n', 1)
    patched = True

# Replace json.loads with json_repair.loads in the triage parsing
if 'triage_data = json.loads(content)' in content:
    content = content.replace('triage_data = json.loads(content)', 'triage_data = json_repair.loads(content)')
    patched = True

if patched:
    with open(intent_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Patched intent.py')
else:
    print('intent.py already patched or pattern not found')

# --- Patch 2: capability_analyzer.py _introspect_analysis ---
cap_path = r'C:\Users\HP\nanobot\nanobot\agent\capability_analyzer.py'
with open(cap_path, 'r', encoding='utf-8') as f:
    content = f.read()

patched2 = False

# Fix the introspection pass json.loads
if 'result = json.loads(content.strip())' in content:
    content = content.replace('result = json.loads(content.strip())', 'result = json_repair.loads(content.strip())')
    patched2 = True

if patched2:
    with open(cap_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Patched capability_analyzer.py introspection')
else:
    print('capability_analyzer.py introspection already patched or pattern not found')
