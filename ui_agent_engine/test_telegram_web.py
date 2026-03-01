import time
import sys
import os
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from agent_core.ui_agent import UIAgent

def test_telegram_web():
    agent = UIAgent()
    
    # We bypass the LLM verbal goal planner to directly test the perception and execution engine
    print("\n--- Starting Telegram Web Test ---")
    
    tasks = [
        # Step 1: Click the Google Chrome application icon on the desktop/taskbar
        {"action": "click", "target": "Google Chrome icon", "description": "To open the Google Chrome browser window and bring it to the foreground."},
        
        # Step 2: Wait for it to open
        {"action": "wait", "duration": 3.0, "description": "To allow the browser window to fully load."},
        
        # Step 3: Open a new tab to ensure a clean address bar
        {"action": "hotkey", "keys": ["ctrl", "t"], "description": "To open a fresh new tab in Chrome."},
        
        # Step 4: Short wait for the new tab
        {"action": "wait", "duration": 1.0, "description": "To wait for the new tab UI to render."},
        
        # Step 5: Type the URL and press enter
        {"action": "type", "text": "web.telegram.org", "description": "To input the Telegram Web URL into the address bar."},
        {"action": "press", "key": "enter", "description": "To navigate to the typed URL."}
    ]
    
    agent.goal_manager.current_goal = "Open Telegram Web in Chrome"
    agent.goal_manager.subtasks = tasks
    
    # Run the continuous execution loop
    agent.run()
    
if __name__ == "__main__":
    test_telegram_web()
