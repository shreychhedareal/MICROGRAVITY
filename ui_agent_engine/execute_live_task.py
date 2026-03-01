import sys
import os
import time
from pathlib import Path

# Set the key for this execution
os.environ["GEMINI_API_KEY"] = "INSERT_API_KEY"

# Add project root and src to path
project_root = Path(r"C:\Users\HP\Downloads\nanobot\ui_agent_engine")
sys.path.append(str(project_root / "src"))

from agent_core.ui_agent import UIAgent

def execute_user_task():
    print("==================================================")
    print("   Live UI Task Execution: Open CMD & `cd Downloads`")
    print("==================================================\n")
    
    # 1. Initialize Agent
    print("[1] Initializing UIAgent and connecting Live Stream WebSocket...")
    agent = UIAgent()
    agent._start_live_stream()
    
    print("[2] Waiting 8 seconds for WebSocket to establish...")
    time.sleep(8)
    
    if agent.live_streamer.is_streaming:
         print("[+] Live Stream is ACTIVE.")
    else:
         print("[-] Live Stream failed to connect. Ensure GEMINI_API_KEY is correct.")
         print("    -> Architecture is defaulting to static vision.")

    print("\n[3] Dispatching Action Queue...")
    
    # Define our action queue manually to ensure we hit the Live API for visual resolution
    # instead of replying on the GoalManager LLM which might not be configured.
    actions = [
        # This is the key step: The predictor will query the Live Stream to find the Start Button
        {"action": "click", "target": "Windows Start Button", "app_window": "Desktop"},
        
        # Wait for start menu to pop up
        {"action": "wait", "duration": 1.5},
        
        # Type 'cmd'
        {"action": "type", "text": "cmd"},
        
        # Wait for search results
        {"action": "wait", "duration": 1.5},
        
        # Hit Enter to open Command Prompt
        {"action": "press", "key": "enter"},
        
        # Wait for terminal to open
        {"action": "wait", "duration": 2.0},
        
        # Type directory change
        {"action": "type", "text": "cd Downloads"},
        
        # Hit Enter
        {"action": "press", "key": "enter"},
        
        # Pause to let the user see the result
        {"action": "wait", "duration": 3.0},
    ]
    
    for idx, action in enumerate(actions, 1):
        print(f"\n--- [Step {idx}] Executing: {action['action']} ---")
        try:
            agent._execute_action(action)
        except Exception as e:
            print(f"[-] Execution failed on action {action}: {e}")
            break
            
    # Cleanup
    print("\n[4] Task queue completed. Shutting down...")
    agent._stop_live_stream()
    print("==================================================")

if __name__ == "__main__":
    execute_user_task()
