import sys
import os

def patch_file(filepath, strings_to_replace):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        modified = False
        for old, new in strings_to_replace:
            if old in content:
                content = content.replace(old, new)
                modified = True
                
        if modified:
            if "import json_repair" not in content:
                content = content.replace("import json", "import json\nimport json_repair", 1)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Patched: {filepath}")
        else:
            print(f"No changes needed or already patched: {filepath}")
    except Exception as e:
        print(f"Error patching {filepath}: {e}")

if __name__ == "__main__":
    base_dir = r"C:\Users\HP\nanobot"
    
    # 1. Patch capability_analyzer.py
    cap_file = os.path.join(base_dir, "nanobot", "agent", "capability_analyzer.py")
    cap_replacements = [
        ("return json.loads(content.strip())", "return json_repair.loads(content.strip())")
    ]
    patch_file(cap_file, cap_replacements)
    
    # 2. Patch introspection.py
    intro_file = os.path.join(base_dir, "nanobot", "agent", "introspection.py")
    intro_replacements = [
        ("result = json.loads(content.strip())", "result = json_repair.loads(content.strip())"),
        ('logger.error("Analysis introspection failed: %s", e)', 'logger.error("Analysis introspection failed: %s", e)') # unchanged but good to check
    ]
    patch_file(intro_file, intro_replacements)
    
    print("Patching complete.")
