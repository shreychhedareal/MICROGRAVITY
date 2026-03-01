import sys
import os

# Add the 'src' directory to the Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from perception.screen import WindowObserver

if __name__ == "__main__":
    # Point to short-term diagnostics for the test
    observer = WindowObserver(output_dir='agent_memory/short_term/diagnostics')
    
    print("Currently visible windows:")
    titles = observer.get_window_titles()
    for t in titles:
        print(f" - {t}")
        
    print("\nAttempting to capture a few common background apps if they are open:")
    # Trying partial matches for common apps you might have open
    targets = ["Notepad", "Chrome", "Edge", "Code", "Discord", "Spotify", "Explorer", "Meet"]
    
    captured_files = []
    for target in targets:
        filepath = observer.capture_window_by_title(target)
        if filepath:
            captured_files.append(filepath)
            
    print(f"\nSuccessfully stored {len(captured_files)} background window buffers!")
