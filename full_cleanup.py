import os
import shutil
import json

base_path = r'C:\Users\HP\.nanobot\workspace'

# 1. Clear sessions
sessions_path = os.path.join(base_path, 'sessions')
if os.path.exists(sessions_path):
    for f in os.listdir(sessions_path):
        if f.endswith('.jsonl'):
            with open(os.path.join(sessions_path, f), 'w') as fh:
                fh.write('')
            print(f'Cleared session: {f}')

# 2. Clear memory files
memory_path = os.path.join(base_path, 'memory')
memory_files = {
    'HISTORY.md': '# History\n\n*Log of previous events and conversations.*\n\n---\n',
    'MEMORY.md': '# Memory\n\n*Persistent memory and learned insights.*\n\n---\n',
    'PROFILE.md': '# User Profile\n\n*Learned preferences and value systems.*\n\n---\n',
    'EXPERIENCE_LEDGER.md': '# Experience Ledger\n\n*Documented complex task orchestrations.*\n\n---\n',
    'EVOLUTION_LEDGER.json': '[]',
    'MACHINE_ENV.md': '# Machine Environment\n\n*Configuration and environment details.*\n\n---\n',
    'REPO_CATALOG.md': '# Repository Catalog\n\n*List of known repositories and their purpose.*\n\n---\n',
    'UI_ATLAS.md': '# UI Atlas\n\n*Visual coordinates and UI patterns.*\n\n---\n',
    'INTROSPECTION_AUDIT.json': '[]'
}

for filename, initial_content in memory_files.items():
    file_path = os.path.join(memory_path, filename)
    if os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as fh:
            fh.write(initial_content)
        print(f'Reset memory file: {filename}')

# 3. Clear LMDB and Vector Store
for store in ['lmdb_store', 'vector_store']:
    store_path = os.path.join(memory_path, store)
    if os.path.exists(store_path):
        shutil.rmtree(store_path)
        os.makedirs(store_path)
        print(f'Wiped store: {store}')

# 4. Remove scratch scripts from workspace root
scratch_patterns = [
    'analyze_screenshot_ocr.py',
    'open_google.py',
    'reddit_login_selenium.py',
    'take_screenshot.py',
    'type_notepad.py',
    'desktop_screenshot.png',
    'temp_screenshot.png'
]

for pattern in scratch_patterns:
    p = os.path.join(base_path, pattern)
    if os.path.exists(p):
        os.remove(p)
        print(f'Removed scratch file: {pattern}')

# 5. Clear vision cache
cache_path = os.path.join(base_path, '.cache', 'vision')
if os.path.exists(cache_path):
    shutil.rmtree(cache_path)
    os.makedirs(cache_path)
    print('Cleared vision cache')

