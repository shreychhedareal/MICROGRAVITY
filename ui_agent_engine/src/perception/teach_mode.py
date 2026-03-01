import time
import os
import threading
from typing import List, Dict, Any
from pynput import mouse, keyboard
from src.perception.screen import ScreenObserver
from src.perception.spatial_understanding.gemini_service import GeminiSpatialService

class TeachModeObserver:
    """
    Records kinesthetic user actions (clicks, drags, keyboard) and synchronizes them
    with visual 'Before' and 'After' frames for Semantic Summarization by the VLM.
    """
    def __init__(self):
        self.screen_obs = ScreenObserver()
        self.gemini = GeminiSpatialService(api_key=os.environ.get("GEMINI_API_KEY", ""))
        
        self.is_recording = False
        self.action_history: List[Dict[str, Any]] = []
        
        self.mouse_listener = None
        self.keyboard_listener = None
        
        # We need a continuous screenshot buffer to always have a "Before" image
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.capture_thread = None

    def _continuous_capture(self):
        """Runs in background, grabbing frames at 5 FPS so we always have a recent 'Before' state."""
        local_obs = ScreenObserver()
        while self.is_recording:
            frame_path = local_obs.capture()
            with self.frame_lock:
                self.latest_frame = frame_path
            time.sleep(0.2) # ~5 FPS

    def start_recording(self):
        print("[Teach Mode] Starting Observation...")
        self.is_recording = True
        self.action_history = []
        
        # Start Vision Buffer
        self.capture_thread = threading.Thread(target=self._continuous_capture, daemon=True)
        self.capture_thread.start()
        
        # Start Kinesthetic Listeners
        self.mouse_listener = mouse.Listener(
            on_click=self.on_click,
            on_scroll=self.on_scroll
        )
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press
        )
        
        self.mouse_listener.start()
        self.keyboard_listener.start()
        print("[Teach Mode] Listening for user interactions...")

    def stop_recording(self):
        print("[Teach Mode] Stopping Observation...")
        self.is_recording = False
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.capture_thread:
            self.capture_thread.join()
            
        print(f"[Teach Mode] Captured {len(self.action_history)} significant actions.")
        return self.action_history

    def _record_event_task(self, event_type: str, details: Dict[str, Any], before_img: Any):
        # Wait a moment for UI to react to the click/key before taking the 'After' shot
        time.sleep(0.5) 
        local_obs = ScreenObserver()
        after_img = local_obs.capture()
        
        action = {
            "timestamp": time.time(),
            "type": event_type,
            "details": details,
            "before_frame": before_img,
            "after_frame": after_img
        }
        self.action_history.append(action)
        print(f"[Teach Mode] Recorded: {event_type} at {details}")

    def _record_event(self, event_type: str, details: Dict[str, Any]):
        """General method to record an event and sync its before/after frames."""
        with self.frame_lock:
            before_img = self.latest_frame
            
        # Spawn a thread so we don't block the pynput listener (which freezes the mouse)
        t = threading.Thread(target=self._record_event_task, args=(event_type, details, before_img))
        t.daemon = True
        t.start()

    def on_click(self, x, y, button, pressed):
        if pressed:
            # We only record the mouse 'down' (click) for simplicity. 
            # Advanced dragging requires tracking mouse move while pressed.
            self._record_event('click', {'x': x, 'y': y, 'button': str(button)})

    def on_scroll(self, x, y, dx, dy):
        self._record_event('scroll', {'x': x, 'y': y, 'dx': dx, 'dy': dy})

    def on_press(self, key):
        # We only record 'significant' keys like Enter, Tab, or hotkeys for sequence breaking
        try:
            char = key.char
            # Could record massive typings, but typically VLMs are better at 
            # seeing the final typed text in the 'After' frame. 
            # We record special keys to demarcate steps.
        except AttributeError:
            if key in [keyboard.Key.enter, keyboard.Key.tab, keyboard.Key.esc]:
                self._record_event('key_press', {'key': str(key)})
                
    def summarize_workflow(self, task_name: str) -> str:
        """Sends the recorded kinesthetic + visual history to Gemini to generate Semantic Blueprints."""
        print(f"[Teach Mode] Sending {len(self.action_history)} steps to VLM for summarization...")
        
        if not self.action_history:
            return "No actions recorded."
            
        import PIL.Image
        from google import genai
        
        # We will bypass the strict `GeminiSpatialService` bounds logic and use the raw client 
        # for a complex multi-modal prompt.
        prompt = f"Analyze the following {len(self.action_history)} UI interactions for the task '{task_name}'.\n"
        prompt += "For each step, you are given a Before image, a raw coordinate action, and an After image.\n"
        prompt += "Please output a JSON summary detailing the semantic purpose of the task, and an array of 'ActionBlueprints' for each step.\n"
        prompt += "A blueprint must have 'action_type', 'target_x', 'target_y', 'target_label', 'easing_func'.\n\n"
        
        contents = [prompt]
        
        for i, action in enumerate(self.action_history):
            contents.append(f"--- Step {i+1} ---")
            contents.append(f"Action: {action['type']}, Details: {action['details']}")
            
            # Load images
            try:
                b_img = PIL.Image.open(action['before_frame'])
                a_img = PIL.Image.open(action['after_frame'])
                contents.append("Before:")
                contents.append(b_img)
                contents.append("After:")
                contents.append(a_img)
            except Exception as e:
                print(f"Failed to load images for step {i+1}: {e}")
                
        try:
            print("[Teach Mode] Awaiting Gemini 2.5 Flash Multi-Modal Analysis...")
            response = self.gemini.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=genai.types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json"
                )
            )
            return response.text
        except Exception as e:
            return f"VLM Summarization Failed: {e}"
