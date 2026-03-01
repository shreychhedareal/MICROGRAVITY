import tkinter as tk
from threading import Thread
import time

class HUDOverlay:
    """
    A transparent, always-on-top overlay to display agent status and intent.
    """
    def __init__(self):
        self.root = None
        self.label_goal = None
        self.label_action = None
        self.label_status = None
        self.canvas = None
        self.crosshair = None
        
        self.goal_text = "Goal: Initializing..."
        self.action_text = "Action: Idle"
        self.status_text = "Live Stream: Offline"
        
        self._thread = Thread(target=self._run_tk, daemon=True)
        self._thread.start()
        
    def _run_tk(self):
        self.root = tk.Tk()
        self.root.title("UI Agent HUD")
        
        # Make transparent and always on top
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "black")
        self.root.overrideredirect(True) # Remove title bar
        
        # Position at the top right
        screen_width = self.root.winfo_screenwidth()
        self.root.geometry(f"400x150+{screen_width - 420}+20")
        
        self.root.config(bg="black")
        
        # Status Labels
        font_style = ("Consolas", 12, "bold")
        
        self.label_goal = tk.Label(self.root, text=self.goal_text, fg="#00FF00", bg="black", font=font_style, wraplength=380, justify="left")
        self.label_goal.pack(anchor="w", padx=10, pady=2)
        
        self.label_action = tk.Label(self.root, text=self.action_text, fg="#00FFFF", bg="black", font=font_style, wraplength=380, justify="left")
        self.label_action.pack(anchor="w", padx=10, pady=2)
        
        self.label_status = tk.Label(self.root, text=self.status_text, fg="#FFFF00", bg="black", font=font_style)
        self.label_status.pack(anchor="w", padx=10, pady=2)
        
        # Full screen canvas for crosshair (if needed)
        # Note: A full screen transparent window might interfere with clicks.
        # We'll stick to the info box for now.
        
        self._update_loop()
        self.root.mainloop()

    def _update_loop(self):
        if self.root:
            self.label_goal.config(text=self.goal_text)
            self.label_action.config(text=self.action_text)
            self.label_status.config(text=self.status_text)
            self.root.after(100, self._update_loop)

    def update_goal(self, text):
        self.goal_text = f"Goal: {text}"

    def update_action(self, text):
        self.action_text = f"Action: {text}"

    def update_status(self, is_streaming):
        status = "ONLINE" if is_streaming else "OFFLINE"
        self.status_text = f"Live Stream: {status}"
        
    def stop(self):
        if self.root:
            self.root.quit()

if __name__ == "__main__":
    # Test standalone
    hud = HUDOverlay()
    time.sleep(2)
    hud.update_goal("Open CMD and cd Downloads")
    hud.update_action("Clicking Start Button")
    hud.update_status(True)
    time.sleep(5)
    hud.stop()
