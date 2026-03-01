import time
import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from perception.teach_mode import TeachModeObserver

def test_teach_mode():
    observer = TeachModeObserver()
    
    print("\n--- Testing Teach Mode Kinesthetic Recording ---")
    observer.start_recording()
    
    print("\nPlease click around and press some keys (like Enter or Tab)...")
    print("Recording will stop in 10 seconds.")
    
    time.sleep(10)
    
    history = observer.stop_recording()
    print("\n--- Recording Finished ---")
    print(f"Captured {len(history)} kinesthetic events.")
    
    if len(history) > 0:
        print("\nSending to VLM (Gemini 2.5 Flash) for testing...")
        # We pass a dummy task name for testing
        result = observer.summarize_workflow("Test Workflow Observation")
        print("\n--- VLM Summary Result ---")
        print(result)

if __name__ == "__main__":
    test_teach_mode()
