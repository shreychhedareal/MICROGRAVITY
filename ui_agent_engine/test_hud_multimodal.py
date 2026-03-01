import sys
import os
import time
from pathlib import Path

# Add src to path
project_root = Path(os.getcwd())
sys.path.append(str(project_root / "src"))

from agent_core.ui_agent import UIAgent

def run_hud_test():
    print("==================================================")
    print("      Integrated Multimodal HUD & Live Test")
    print("==================================================\n")
    
    # 1. Initialize Agent
    print("[1] Initializing UIAgent (HUD will appear Top-Right)...")
    agent = UIAgent()
    
    # 2. Hand off task
    task = "Open the Command Prompt, change directory to Downloads, and say 'Action Complete' via audio."
    print(f"[2] Goal: {task}")
    agent.receive_task(task)
    
    # 3. Run Agent (This starts streamer + HUD internally)
    print("[3] Starting execution loop...")
    try:
        agent.run()
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
    finally:
        print("[4] Cleaning up...")
        agent._stop_live_stream()
        if hasattr(agent, 'hud'):
            agent.hud.stop()
    
    print("==================================================")

if __name__ == "__main__":
    os.environ["GEMINI_API_KEY"] = "INSERT_API_KEY"
    run_hud_test()
