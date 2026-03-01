import os
import json
path = r'C:\Users\HP\.nanobot\workspace\memory\EVOLUTION_LEDGER.json'
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Filter out entries mentioning web_search
    cleaned = [entry for entry in data if 'web_search' not in str(entry).lower()]
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, indent=4)
    print('Cleaned EVOLUTION_LEDGER.json')
