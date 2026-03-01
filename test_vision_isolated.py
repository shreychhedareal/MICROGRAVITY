import os
import base64
import asyncio
from ui_agent_prototype.perception import PerceptionEngine
from nanobot.providers.litellm_provider import LiteLLMProvider

# Inject the user's provided API key into the environment
os.environ['GEMINI_API_KEY'] = "INSERT_API_KEY"

def test_vision():
    p = PerceptionEngine()
    img_path = p.capture_screenshot()
    print("Screenshot captured. Asking Gemini...")
    res = p.analyze_with_vision(img_path, "Look closely at the screen. What tabs on Google Chrome are open? Name them explicitly.")
    
    with open("vision_result.txt", "w", encoding="utf-8") as f:
        f.write(res.get("vision_analysis", str(res)))
    print("Result saved to vision_result.txt")

if __name__ == "__main__":
    test_vision()
