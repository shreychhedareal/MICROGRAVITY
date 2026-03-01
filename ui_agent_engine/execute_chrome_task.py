import sys
import os
import time
from pathlib import Path

# Add src to path
project_root = Path(os.getcwd())
sys.path.append(str(project_root / "src"))

from agent_core.ui_agent import UIAgent

def execute_chrome_task():
    print("==================================================")
    print("      Chrome -> WhatsApp Task with HUD & Live")
    print("==================================================\n")
    
    agent = UIAgent()
    
    # 1. Start Streamer and HUD
    print("[1] Initializing Multimodal Session...")
    agent._start_live_stream()
    agent.hud.update_status(True)
    agent.hud.update_goal("Open Chrome and type whatsapp")
    
    time.sleep(5) # Wait for stream
    
    actions = [
        {"action": "click", "target": "Windows Start Button", "app_window": None},
        {"action": "wait", "duration": 1.5},
        {"action": "type", "text": "chrome"},
        {"action": "wait", "duration": 1.5},
        {"action": "press", "key": "enter"},
        {"action": "wait", "duration": 4.0}, # Wait for Chrome to load
        {"action": "type", "text": "whatsapp"},
        {"action": "wait", "duration": 1.0},
        {"action": "press", "key": "enter"},
        {"action": "wait", "duration": 3.0}
    ]
    
    for idx, action in enumerate(actions, 1):
        print(f"\n--- [Step {idx}] {action['action']} ---")
        agent.hud.update_action(f"Step {idx}: {action.get('action')} on {action.get('target', 'Input')}")
        try:
            agent._execute_action(action)
        except Exception as e:
            print(f"[-] Action failed: {e}")
            break
            
    print("\n[!] Task complete. Cleaning up...")
    agent._stop_live_stream()
    agent.hud.stop()
    print("==================================================")

if __name__ == "__main__":
    os.environ["GEMINI_API_KEY"] = "INSERT_API_KEY"
    execute_chrome_task()
