import os

targets = [
    r'C:\Users\HP\nanobot\prompt_output.txt',
    r'C:\Users\HP\nanobot\README.md',
    r'C:\Users\HP\nanobot\test_trace2.txt'
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
