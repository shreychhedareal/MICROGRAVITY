import time
import sys
import os
from typing import Dict, Any, Optional
from pathlib import Path

# Add the 'src' directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui_controller.mouse import MouseController
from ui_controller.keyboard import KeyboardController
from ui_controller.window_manager import WindowManager
from perception.screen import ScreenObserver, WindowObserver
from perception.vision_analyzer import VisionAnalyzer
from planning.goal_manager import GoalManager
from planning.action_predictor import ActionPredictor
from planning.learning_loop import LearningLoop
from agent_core.ui_memory_agent import UIMemoryAgent
from ui_controller.live_streamer import GeminiLiveStreamer
from ui_controller.hud_overlay import HUDOverlay
import win32gui
import win32con
import asyncio
import threading


class UIAgent:
    """
    The main orchestrator that ties together all modules:
    Perception, Planning, and Action into a continuous loop.
    """
    def __init__(self):
        print("[UIAgent] Initializing agent modules...", flush=True)
        self.mouse = MouseController(base_speed=1.0)
        print("[UIAgent] Mouse initialized", flush=True)
        self.keyboard = KeyboardController(wpm=60)
        print("[UIAgent] Keyboard initialized", flush=True)
        
        self.workspace_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.memory_agent = UIMemoryAgent(self.workspace_path)
        print("[UIAgent] UI Memory Agent initialized", flush=True)
        
        # Inject short-term paths into observers
        screenshot_dir = str(self.memory_agent.short_term_dir / "screenshots")
        self.screen_observer = ScreenObserver(output_dir=screenshot_dir)
        print("[UIAgent] Screen observer initialized", flush=True)
        self.window_observer = WindowObserver(output_dir=screenshot_dir)
        print("[UIAgent] Window observer initialized", flush=True)
        self.vision = VisionAnalyzer()
        print("[UIAgent] Vision analyzer initialized", flush=True)
        
        self.goal_manager = GoalManager()
        self.predictor = ActionPredictor(self.vision, memory_agent=self.memory_agent, screen_observer=self.screen_observer)
        self.learning_loop = LearningLoop(self.vision, self.predictor)
        self.window_manager = WindowManager()
        print("[UIAgent] Planning and Management modules initialized", flush=True)
        
        # Initialize Gemini Live Streamer (Disabled by default until started)
        self.live_streamer = GeminiLiveStreamer()
        self._streaming_thread = None
        self._loop = asyncio.new_event_loop()
        
        self.is_running = False
        self.hud = HUDOverlay() # Initialize HUD
        
        # --- Bootstrap Static GUI Map into CV Memory ---
        self._bootstrap_static_memory()
        print("[UIAgent] Bootstrap complete", flush=True)

    def _start_live_stream(self):
         """Starts the asyncio event loop in a background thread to maintain the WebSocket."""
         def run_loop(loop):
             asyncio.set_event_loop(loop)
             
             system_prompt = "You are a UI Assistant examining a live screen. I will send you questions about UI elements. Provide their bounding boxes and predict the correct human interaction (e.g. 'hover', 'single_click')."
             
             async def runner():
                 # Create the stream task which will internally sleep until self.is_streaming becomes True
                 async def safe_stream():
                      while not self.live_streamer.is_streaming:
                           await asyncio.sleep(0.5)
                      await self.live_streamer.stream_screen_loop(fps=0.5)
                      
                 loop.create_task(safe_stream())
                 
                 # Block on the context manager session
                 await self.live_streamer.start_session(system_instruction=system_prompt)
                 
             try:
                 loop.run_until_complete(runner())
             except Exception as e:
                 print(f"[UIAgent - LiveStreamer] Could not establish live session: {e}")
                 
         self._streaming_thread = threading.Thread(target=run_loop, args=(self._loop,), daemon=True)
         self._streaming_thread.start()

    def _stop_live_stream(self):
         """Safely shuts down the background WebSocket."""
         if self.live_streamer and self.live_streamer.is_streaming:
             asyncio.run_coroutine_threadsafe(self.live_streamer.disconnect(), self._loop)
         if self._loop.is_running():
             self._loop.call_soon_threadsafe(self._loop.stop)


    def _bootstrap_static_memory(self):
        """Finds the most recent gui_map and raw screenshot in agent_memory and loads them."""
        import glob
        import os
        
        # Point to Long-Term track for structural authority
        json_dir = self.memory_agent.long_term_dir / "predicted_outputs"
        img_dir = self.memory_agent.long_term_dir / "raw_screenshots"
        
        json_files = glob.glob(os.path.join(str(json_dir), "gui_map_*.json"))
        if not json_files:
            print("[UIAgent] No static gui_map JSON found to bootstrap.")
            return
            
        latest_json = max(json_files, key=os.path.getctime)
        # Extract timestamp: gui_map_1234567.json -> 1234567
        filename = os.path.basename(latest_json)
        timestamp = filename.replace("gui_map_", "").replace(".json", "")
        
        # Find matching raw screenshot
        raw_image = os.path.join(str(img_dir), f"capture_{timestamp}.png")
        
        if os.path.exists(raw_image):
            self.predictor.load_static_map(latest_json, raw_image)
        else:
            print(f"[UIAgent] Missing matching raw screenshot for {latest_json}")

    def receive_task(self, task_description: str):
        """Entry point for Swarm to hand off a task."""
        self.goal_manager.set_goal(task_description)
        self.hud.update_goal(task_description)

    def run(self):
        """
        The main Observe-Think-Act loop.
        """
        self.is_running = True
        print("[UIAgent] Starting execution loop...")
        
        # Boot up the Live Streamer in the background
        self._start_live_stream()
        self.hud.update_status(True)
        
        while self.is_running and not self.goal_manager.goal_completed():
            action = self.goal_manager.get_next_action()
            if not action:
                 time.sleep(1)
                 continue
                 
            self._execute_action(action)
            
        print("[UIAgent] Goal completed or execution stopped.")
        self._stop_live_stream()
        self.is_running = False


    def _execute_action(self, action: Dict[str, Any]):
        """Executes a single logical action, predicting parameters and evaluating success."""
        
        target = action.get('target', '')
        target_app = action.get('app_window')
        context = target_app if target_app else 'Desktop'
        timestamp = int(time.time()*1000)
        
        # Inject the live streamer into the action context for the predictor
        action['live_streamer'] = self.live_streamer
        self.hud.update_action(f"{action.get('action')} on {target}")
        
        # 1. Prediction with skip-perception hint
        # We try a 'dry run' of prediction to see if we can skip the screenshot
        params = {}
        if not self.live_streamer.is_streaming:
             params = self.predictor.predict_action_parameters(action, screen_image_path=None)
        
        state_before = None

        if params and params.get("predicted_as") == "invariant":
            print(f"[UIAgent] Optimization: Skipping 'before' screenshot for invariant '{target}' in stable context.")
        else:
            # Observe Before State: If action specifies an app window, capture just that
            if target_app:
                print(f"[UIAgent] Capturing background buffer for app '{target_app}'")
                filename = f"before_{target_app}_{timestamp}.png"
                full_path = str(self.memory_agent.short_term_dir / "screenshots" / filename)
                state_before = self.window_observer.capture_window_by_title(target_app, filename=full_path)
                # Fallback to full screen if window not found
                if not state_before:
                    filename = f"before_fallback_{timestamp}.png"
                    full_path = str(self.memory_agent.short_term_dir / "screenshots" / filename)
                    state_before = self.screen_observer.capture(filename=full_path)
            else:
                filename = f"before_{timestamp}.png"
                full_path = str(self.memory_agent.short_term_dir / "screenshots" / filename)
                state_before = self.screen_observer.capture(filename=full_path)
            
            # Re-predict with actual image (or trigger live async query natively if streaming)
            if not params or self.live_streamer.is_streaming:
                
                # If streaming, we must block on the Async result from the predictor bridge
                if self.live_streamer.is_streaming:
                     # This is slightly tricky since _execute_action is sync, but we use threadsafe futures
                     import concurrent.futures
                     future = asyncio.run_coroutine_threadsafe(
                         self.predictor._query_live_api(target, action, self.live_streamer), 
                         self._loop
                     )
                     try:
                         # Wait for the WebSocket trip
                         params = future.result(timeout=20.0)
                     except Exception as e:
                         print(f"[UIAgent] Live prediction failed/timeout: {e}. Falling back to static.")
                         params = self.predictor.predict_action_parameters(action, state_before)
                else:
                     params = self.predictor.predict_action_parameters(action, state_before)

        
        # 2. Act (Coordinate Translation & Focus)
        import win32gui # win32con is not needed here anymore
        hwnd = None
        if target_app:
             hwnd = self.window_manager.get_hwnd_by_title(target_app)
             if hwnd:
                  self.window_manager.focus_window(hwnd)
                  # Coordinate translation logic...
                  if isinstance(params, dict) and 'x' in params and 'y' in params:
                      try:
                          client_point = win32gui.ClientToScreen(hwnd, (0, 0))
                          params['x'] = params['x'] + client_point[0]
                          params['y'] = params['y'] + client_point[1]
                          print(f"[UIAgent] Translated relative to global desktop ({params['x']}, {params['y']})")
                      except Exception: pass

        print(f"[UIAgent] Executing {action['action']} with {params}")
        
        # Action Dispatcher
        if action['action'] == 'click':
             if isinstance(params, dict) and 'x' in params and 'y' in params:
                 self.mouse.move_and_click(params['x'], params['y'], human_like=True)
             else:
                 print(f"[UIAgent] WARNING: Could not resolve coordinates for click on {action.get('target')}")
                 
        elif action['action'] == 'double_click':
             if isinstance(params, dict) and 'x' in params and 'y' in params:
                 self.mouse.move_to(params['x'], params['y'], human_like=True)
                 self.mouse.double_click()

        elif action['action'] == 'drag':
             # Resolve destination
             dest_label = action.get('destination')
             dest_params = self.predictor.predict_action_parameters({"action": "click", "target": dest_label}, state_before)
             if 'x' in params and 'y' in params and 'x' in dest_params:
                 self.mouse.drag_to(dest_params['x'], dest_params['y'], source_x=params['x'], source_y=params['y'])

        elif action['action'] == 'type':
             if 'text' in params:
                 self.keyboard.type_text(params['text'])
                 
        elif action['action'] == 'scroll':
             clicks = action.get('amount', 300)
             direction = action.get('direction', 'down')
             self.mouse.scroll(clicks, direction)

        elif action['action'] == 'minimize':
             if hwnd: self.window_manager.minimize(hwnd)
             
        elif action['action'] == 'maximize':
             if hwnd: self.window_manager.maximize(hwnd)

        elif action['action'] == 'resize':
             if hwnd and 'width' in action and 'height' in action:
                  self.window_manager.resize(hwnd, action['width'], action['height'])
                  
        elif action['action'] == 'hotkey':
             if 'keys' in action:
                 self.keyboard.hotkey(*action['keys'])
                 
        elif action['action'] == 'press':
             if 'key' in action:
                 self.keyboard.press_key(action['key'])
                 
        elif action['action'] == 'wait':
             time.sleep(params.get('duration', 1.0))
             
        # Add a small human pause after action
        time.sleep(0.5)
        
        # 4. Observe After State
        if target_app:
            filename = f"after_{target_app}_{timestamp}.png"
            full_path = str(self.memory_agent.short_term_dir / "screenshots" / filename)
            state_after = self.window_observer.capture_window_by_title(target_app, filename=full_path)
            if not state_after:
                filename = f"after_fallback_{timestamp}.png"
                full_path = str(self.memory_agent.short_term_dir / "screenshots" / filename)
                state_after = self.screen_observer.capture(filename=full_path)
        else:
            filename = f"after_{timestamp}.png"
            full_path = str(self.memory_agent.short_term_dir / "screenshots" / filename)
            state_after = self.screen_observer.capture(filename=full_path)
        
        # 5. Evaluate Success (Learning)
        success = self.learning_loop.evaluate_action_success(action, state_before, state_after)
        
        if not success:
             print("[UIAgent] Action failed. Triggering Semantic Recovery Replan...")
             self.goal_manager.replan_recovery(action, state_after, self.vision)

if __name__ == "__main__":
    agent = UIAgent()
    agent.receive_task("Close the Notepad application.")
    agent.run()
