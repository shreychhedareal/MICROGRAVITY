import sys

filepath = r'C:\Users\HP\nanobot\nanobot\agent\tools\capability.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "user_request": {
                        "type": "string",
                        "description": "The specific feature or expansion requested by the user."
                    }
                },
                "required": ["user_request"]
            }
        }'''

new_code = '''    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_request": {
                    "type": "string",
                    "description": "The specific feature or expansion requested by the user."
                }
            },
            "required": ["user_request"]
        }'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched abstract method error.")
else:
    print("Target block not found. It might be slightly different.")
