import sys
import os
import time
from pathlib import Path
import asyncio

# Add project root and src to path
project_root = Path(r"C:\Users\HP\Downloads\nanobot\ui_agent_engine")
sys.path.append(str(project_root / "src"))

from agent_core.ui_agent import UIAgent

def run_live_integration_test():
    print("==================================================")
    print("   UI Agent Live Interaction Feedback Test Run    ")
    print("==================================================\n")
    
    # Check for API key first
    api_key_present = "GEMINI_API_KEY" in os.environ
    print(f"[*] Checking for GEMINI_API_KEY in environment... {'FOUND' if api_key_present else 'NOT FOUND'}")
    
    if not api_key_present:
        print("\n[!] WARNING: You must set the GEMINI_API_KEY environment variable for the live stream to connect.")
        print("    Example (cmd): set GEMINI_API_KEY=your_key_here")
        print("    Example (PS): $env:GEMINI_API_KEY='your_key_here'\n")
    
    # 1. Initialize the Agent
    print("[1] Initializing UIAgent and spawning live streaming loop...")
    try:
        agent = UIAgent()
    except Exception as e:
        print(f"[Error] Failed to initialize UIAgent: {e}")
        return

    # Wait for the background thread to attempt WebSocket connection
    print("[2] Waiting 5 seconds for WebSocket connection attempt...")
    time.sleep(5)
    
    if not agent.live_streamer.is_streaming:
        print("\n[!] Live Streamer is NOT active. Architecture is running in standalone mode.")
    else:
        print("\n[+] Live Streamer IS active. WebSocket connection established.")
        
    print("\n[3] Simulating a Live Prediction Query...")
    print("    -> Action: Click 'Windows Start Button'")
    
    test_action = {
        "action": "click",
        "target": "Windows Start Button",
        "app_window": "Desktop",
        "live_streamer": agent.live_streamer # Inject the streamer as the main loop does
    }
    
    # Force the query through the async bridge
    if agent.live_streamer.is_streaming:
        print("    -> Querying Live API for precise coordinates and biological 'interaction_preference'...")
        try:
            future = asyncio.run_coroutine_threadsafe(
                agent.predictor._query_live_api(test_action['target'], test_action, agent.live_streamer), 
                agent._loop
            )
            params = future.result(timeout=15.0)
            print(f"\n[+] Prediction Success!\n{params}")
            
            if "interaction_preference" in params:
                 print(f"    -> Extracted Human Interaction Preference: {params['interaction_preference']}")
                 
            print("\n[4] Verifying Memory Agent Caching...")
            atlas_entry = agent.memory_agent.recall_element("Desktop", "Windows Start Button")
            if atlas_entry and "interaction_preference" in atlas_entry:
                 print(f"    -> Successfully cached preference to ui_atlas.json: {atlas_entry['interaction_preference']}")
            else:
                 print("    -> Cache verification failed.")
                 
        except Exception as e:
            print(f"\n[-] Live prediction failed or timed out: {e}")
    else:
        print("    -> Skipping live network query due to inactive stream.")
        print("    -> Falling back to simulated static vision path to prove structural integrity...")
        fallback_params = agent.predictor._query_static_vlm(
            target=test_action["target"], 
            action=test_action, 
            screen_image_path="dummy_path.png", 
            target_key="windows start button"
        )
        print(f"\n[+] Fallback Prediction Executed: {fallback_params}")
        
    # Cleanup
    print("\n[5] Shutting down agent and background threads...")
    agent._stop_live_stream()
    print("==================================================")
    print("                   Test Complete                  ")
    print("==================================================")

if __name__ == "__main__":
    run_live_integration_test()
