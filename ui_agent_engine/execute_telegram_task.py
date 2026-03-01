import sys
import os
import time
from pathlib import Path

# Add src to path
project_root = Path(os.getcwd())
sys.path.append(str(project_root / "src"))

from agent_core.ui_agent import UIAgent

def execute_telegram_task():
    print("==================================================")
    print("      Telegram Web: Bulletproof Search")
    print("==================================================\n")
    
    agent = UIAgent()
    
    try:
        # Start session
        agent._start_live_stream()
        agent.hud.update_status(True)
        agent.hud.update_goal("Search & Extract 'openclaw'")
        time.sleep(5)
        
        # 1. Open New Tab
        print("[1] Opening Telegram Web...")
        hwnd = agent.window_manager.get_hwnd_by_title("Google Chrome")
        if hwnd: agent.window_manager.focus_window(hwnd)
        time.sleep(1)
        agent.keyboard.hotkey('ctrl', 't')
        time.sleep(1)
        agent.keyboard.type_text('https://web.telegram.org')
        agent.keyboard.press_key('enter')
        time.sleep(20) # Heavy load
        
        # 2. Search
        print("[2] Searching for 'openclaw'...")
        action_search = {"action": "click", "target": "Search chats", "app_window": "Telegram Web - Google Chrome"}
        agent._execute_action(action_search)
        time.sleep(1)
        agent.keyboard.type_text("openclaw")
        time.sleep(5)
        
        # 3. Open Result
        print("[3] Opening 'Open claw'...")
        action_select = {"action": "click", "target": "Open claw chat item", "app_window": "Telegram Web - Google Chrome"}
        agent._execute_action(action_select)
        time.sleep(5)
        
    except Exception as e:
        print(f"[-] Automation Step Failure: {e}")
    finally:
        # 4. Mandatory Screenshot
        print("[4] Capturing Final Result...")
        timestamp = int(time.time()*1000)
        filename = f"telegram_bulletproof_{timestamp}.png"
        full_path = str(agent.memory_agent.short_term_dir / "screenshots" / filename)
        agent.screen_observer.capture(filename=full_path)
        print(f"[!] Saved screenshot to: {filename}")
        
        # Cleanup
        agent._stop_live_stream()
        agent.hud.stop()
        print("==================================================")

if __name__ == "__main__":
    os.environ["GEMINI_API_KEY"] = "INSERT_API_KEY"
    execute_telegram_task()
