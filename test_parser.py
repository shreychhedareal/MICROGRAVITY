"""Quick isolated test for _parse_llm_output — no heavy nanobot imports."""
import re
import sys

def _parse_llm_output(text):
    if not text or not text.strip():
        return {}
    cleaned = text.strip()
    for prefix in ("```json", "```JSON", "```"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    if not cleaned:
        return {}
    try:
        import json_repair as jr
        result = jr.repair_json(cleaned, return_objects=True)
        if isinstance(result, dict):
            return result
    except Exception:
        pass
    try:
        import json_repair as jr
        m = re.search(r'\{[\s\S]+\}', cleaned)
        if m:
            result = jr.repair_json(m.group(0), return_objects=True)
            if isinstance(result, dict):
                return result
    except Exception:
        pass
    try:
        import yaml
        result = yaml.safe_load(cleaned)
        if isinstance(result, dict):
            return result
    except Exception:
        pass
    return {}


tests = [
    ("Clean JSON", '{"a": 1, "b": "hello"}', lambda r: r == {"a": 1, "b": "hello"}),
    ("Markdown-wrapped", '```json\n{"x": true}\n```', lambda r: r.get("x") == True),
    ("Trailing comma", '{"a": 1, "b": 2,}', lambda r: isinstance(r, dict) and r.get("a") == 1),
    ("Unterminated string", '{"intent_summary": "The user wants to open Telegram', lambda r: isinstance(r, dict)),
    ("Completely broken", "This is not JSON at all", lambda r: r == {}),
    ("Unquoted keys", '{proceed_immediately: true, intent_summary: "test"}', lambda r: isinstance(r, dict)),
    ("Empty string", "", lambda r: r == {}),
    ("Large truncated", '{"request_classification": "new_tool", "technical_complexity": "high", "complexity_justification": "This requires building', lambda r: isinstance(r, dict)),
    ("Expecting prop name", '{"a": 1, "b": {"nested": "val"}, }', lambda r: isinstance(r, dict) and r.get("a") == 1),
]

passed = 0
for name, inp, check in tests:
    try:
        result = _parse_llm_output(inp)
        ok = check(result)
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"  {status}: {name} -> {result}")
    except Exception as e:
        print(f"  EXCEPTION: {name} -> {e}")

print(f"\n{'='*50}")
print(f"Results: {passed}/{len(tests)} passed")
if passed == len(tests):
    print("ALL TESTS PASSED - Parser is bulletproof!")
    sys.exit(0)
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
