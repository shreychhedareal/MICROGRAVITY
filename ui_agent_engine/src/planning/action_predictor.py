from typing import Dict, Any, Optional
import json
import os
import cv2
import numpy as np

class ActionPredictor:
    """
    Predicts the required coordinates or keystrokes for a given logical action 
    based on the current screen state. Uses a Hybrid CV+VLM approach:
    1. Fast Path: OpenCV Template Matching (Zero Latency, < 10ms)
    2. Fallback Path: VLM Query (High Latency, 5-10s)
    """
    def __init__(self, vision_analyzer, memory_agent=None, screen_observer=None):
        self.vision = vision_analyzer
        self.memory_agent = memory_agent
        self.screen_observer = screen_observer
        # RAM Cache: { "target_label": {"coords": (x,y), "template": numpy_bgr_array, "bbox": (x,y,w,h)} }
        self.memory = {}

    def load_static_map(self, json_path: str, raw_image_path: str):
        """Bootstraps the CV memory cache with thousands of templates from a static GUI map run."""
        if not os.path.exists(json_path) or not os.path.exists(raw_image_path):
            print(f"[ActionPredictor] Bootstrap files not found: {json_path} or {raw_image_path}")
            return
            
        print(f"[ActionPredictor] Bootstrapping Memory from {json_path}...")
        try:
            with open(json_path, 'r') as f:
                gui_map = json.load(f)
                
            raw_img = cv2.imread(raw_image_path)
            if raw_img is None:
                return
                
            loaded_count = 0
            for element in gui_map:
                label = element.get('label')
                # Ignore generic structural labels, keep semantic ones
                if label and label not in ["STRUCTURAL", "TASKBAR"]:
                    coords = element.get('coordinates', {})
                    if not coords:
                        continue
                    x, y, w, h = coords.get('x', 0), coords.get('y', 0), coords.get('width', 0), coords.get('height', 0)
                    
                    # Crop template from raw image
                    # Ensure within bounds
                    x, y = max(0, x), max(0, y)
                    h, w = max(1, h), max(1, w)
                    template = raw_img[y:y+h, x:x+w]
                    
                    if template.size > 0:
                        center_x = x + (w // 2)
                        center_y = y + (h // 2)
                        self.memory[label.lower()] = {
                            "coords": (center_x, center_y),
                            "template": template,
                            "bbox": (x, y, w, h)
                        }
                        loaded_count += 1
            print(f"[ActionPredictor] Bootstrap Complete: {loaded_count} templates cached in RAM.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[ActionPredictor] Bootstrap Failed: {e}")

    def _verify_with_cv(self, template: np.ndarray, current_screen_path: str, threshold: float = 0.85) -> Optional[tuple]:
        """Uses OpenCV template matching to find the template in the current screen. Ultra fast."""
        try:
            current_screen = cv2.imread(current_screen_path)
            if current_screen is None or template is None:
                return None
                
            # Perform normalized cross-correlation
            result = cv2.matchTemplate(current_screen, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= threshold:
                # Match found! Calculate new center based on where it was found
                h, w = template.shape[:2]
                top_left = max_loc
                center_x = top_left[0] + w // 2
                center_y = top_left[1] + h // 2
                print(f"[CV Tracker] MATCH {max_val:.2f} >= {threshold}. Fast Coords: ({center_x}, {center_y})")
                return (center_x, center_y)
            else:
                print(f"[CV Tracker] STALE {max_val:.2f} < {threshold}. Element vanished or changed.")
                return None
        except Exception as e:
            print(f"[CV Tracker] CV Error: {e}")
            return None

    def predict_action_parameters(self, action: Dict[str, Any], screen_image_path: str) -> Dict[str, Any]:
        """
        Takes an abstract action and the current screen, and returns concrete parameters.
        """
        print(f"[ActionPredictor] Predicting parameters for {action['action']} on '{action.get('target', action.get('text'))}'")
        
        target = action.get('target')
        target_key = target.lower() if target else None
        
        if target_key:
            # 1. Check RAM Cache
            if target_key in self.memory:
                print(f"[ActionPredictor] Target '{target}' found in RAM Cache. Verifying with CV...")
                cached_data = self.memory[target_key]
                fast_coords = self._verify_with_cv(cached_data["template"], screen_image_path)
                if fast_coords:
                    # Update Atlas if position shifted significantly
                    if self.memory_agent:
                        context = action.get('app_window', 'Desktop')
                        new_coords = [fast_coords[0] - cached_data["bbox"][2]//2, 
                                     fast_coords[1] - cached_data["bbox"][3]//2,
                                     cached_data["bbox"][2], 
                                     cached_data["bbox"][3]]
                        self.memory_agent.sync_element(context, target, new_coords)
                    
                    return {"x": fast_coords[0], "y": fast_coords[1]}
                del self.memory[target_key]
            
            # 2. Check Persistent UI Atlas
            if self.memory_agent:
                context = action.get('app_window', 'Desktop')
                atlas_data = self.memory_agent.recall_element(context, target)
                if atlas_data:
                    if atlas_data.get("is_invariant"):
                        # Check if context is stable (rect hasn't changed)
                        # If FIXED (Desktop), skip CV if coords exist
                        context_type = self.memory_agent.atlas["contexts"].get(context, {}).get("type", "DYNAMIC")
                        
                        # Invariants in FIXED contexts are always safe to reuse if screen size matches
                        if context_type == "FIXED" and atlas_data.get("coords"):
                            c = atlas_data["coords"]
                            print(f"[ActionPredictor] DIRECT prediction for FIXED invariant '{target}': ({c[0]}, {c[1]})")
                            return {"x": c[0] + c[2]//2, "y": c[1] + c[3]//2, "predicted_as": "invariant"}

                    print(f"[ActionPredictor] Target '{target}' found in UI Atlas. Verifying with CV...")
                    if atlas_data.get("template_path"):
                        res = self.vision.compare_templates(screen_image_path, atlas_data["template_path"])
                        if res:
                            x, y, w, h = res
                            center_x, center_y = x + w//2, y + h//2
                            return {"x": center_x, "y": center_y}
                    
                    # Fallback to coordinate-based prediction if template fails but we have bounds
                    if atlas_data.get("coords"):
                        # This is riskier as windows might move, but useful for static layouts
                        c = atlas_data["coords"]
                        
                        # Return interaction preference if known
                        pref = atlas_data.get("interaction_preference", "default")
                        return {"x": c[0] + c[2]//2, "y": c[1] + c[3]//2, "interaction_preference": pref}

        if action['action'] == 'click':
            # --- 2. FALLBACK PATH: VLM Query ---
            print(f"[ActionPredictor] Target '{target}' not cached or stale. Falling back to VLM...")
            
            # Use Live Stream if available, otherwise static vision
            live_streamer = action.get('live_streamer')
            
            if live_streamer and live_streamer.is_streaming:
                 # This should be called via run_coroutine_threadsafe externally if we are in sync execute_action
                 print("[ActionPredictor] Error: Live streamer passed to sync execute check. Use threadsafe bridge.")
                 return self._query_static_vlm(target, action, screen_image_path, target_key)
            else:
                 return self._query_static_vlm(target, action, screen_image_path, target_key)

    async def _query_live_api(self, target: str, action: Dict[str, Any], live_streamer: Any) -> Dict[str, Any]:
        """Queries the active Gemini Live Streaming session for coordinates and interaction type."""
        print(f"[ActionPredictor] Querying Live Stream for '{target}'...")
        
        # Setup an Event to wait for the callback
        import asyncio
        response_event = asyncio.Event()
        prediction_result = {}
        
        def _live_callback(data: Dict[str, Any]):
            # The streamer parses JSON if possible
            if "bounding_box" in data or "coordinates" in data:
                 prediction_result.update(data)
                 response_event.set()
            elif "text_response" in data:
                 # Attempt rudimentary parsing if the model failed to return strict JSON
                 prediction_result["raw_text"] = data["text_response"]
                 response_event.set()
        
        # Temporarily override the callback
        original_callback = live_streamer.on_response_callback
        live_streamer.set_callback(_live_callback)
        
        prompt = f"""
        Locate the UI element: '{target}'.
        1. Provide its bounding box [ymin, xmin, ymax, xmax] in normalized coordinates (0-1000).
        2. What is the preferred human interaction for this element? (e.g., 'hover', 'single_click', 'double_click', 'drag')
        Respond ONLY in JSON format like: {{"bounding_box": [ymin, xmin, ymax, xmax], "interaction_preference": "single_click"}}
        """
        
        await live_streamer.send_prompt(prompt)
        
        try:
             # Wait up to 10 seconds for the model to reply over the stream
             await asyncio.wait_for(response_event.wait(), timeout=10.0)
             
             # Process result
             if "bounding_box" in prediction_result:
                 bbox = prediction_result["bounding_box"]
                 pref = prediction_result.get("interaction_preference", "single_click")
                 
                 # Convert normalized to screen coords
                 # Using dynamic resolution if available, otherwise fallback to 1920x1080
                 screen_w, screen_h = 1920, 1080 
                 if self.screen_observer:
                     try:
                         monitor = self.screen_observer.sct.monitors[1]
                         screen_w, screen_h = monitor["width"], monitor["height"]
                         print(f"[ActionPredictor] Dynamic Resolution Detected: {screen_w}x{screen_h}")
                     except Exception as e:
                         print(f"[ActionPredictor] Resolution check failed: {e}. Using fallback.")
                 
                 pixel_ymin = int((bbox[0] / 1000) * screen_h)
                 pixel_xmin = int((bbox[1] / 1000) * screen_w)
                 pixel_ymax = int((bbox[2] / 1000) * screen_h)
                 pixel_xmax = int((bbox[3] / 1000) * screen_w)
                 
                 center_x = (pixel_xmin + pixel_xmax) // 2
                 center_y = (pixel_ymin + pixel_ymax) // 2
                 
                 print(f"[ActionPredictor] Live API Found '{target}' at ({center_x}, {center_y}). Prefers: {pref}")
                 
                 # Save to Atlas
                 if self.memory_agent:
                     context = action.get('app_window', 'Desktop')
                     self.memory_agent.remember_element(context, target, {
                         "coords": [pixel_xmin, pixel_ymin, pixel_xmax-pixel_xmin, pixel_ymax-pixel_ymin],
                         "type": "live_discovered",
                         "interaction_preference": pref
                     })
                     
                 return {"x": center_x, "y": center_y, "interaction_preference": pref}
        except asyncio.TimeoutError:
             print("[ActionPredictor] Live API query timed out.")
        finally:
             live_streamer.set_callback(original_callback)
             
        return {"x": 100, "y": 100} # Fallback
    def _query_static_vlm(self, target: str, action: Dict[str, Any], screen_image_path: str, target_key: str) -> Dict[str, Any]:
        """Original static image prompting logic."""
        vlm_response = self.vision.find_element_bbox(screen_image_path, target)
        
        try:
            if "NOT FOUND" not in vlm_response:
                # Clean the string and convert to a list of integers
                clean_text = vlm_response.replace('[', '').replace(']', '').strip()
                ymin, xmin, ymax, xmax = map(int, clean_text.split(','))
                
                # Get actual image dimensions & crop the new template
                img_cv = cv2.imread(screen_image_path)
                img_height, img_width = img_cv.shape[:2]
                
                # Convert Normalized 0-1000 bounds to Actual Screen Pixels
                pixel_xmin = int((xmin / 1000) * img_width)
                pixel_xmax = int((xmax / 1000) * img_width)
                pixel_ymin = int((ymin / 1000) * img_height)
                pixel_ymax = int((ymax / 1000) * img_height)
                
                # Calculate the center point for clicking
                center_x = (pixel_xmin + pixel_xmax) // 2
                center_y = (pixel_ymin + pixel_ymax) // 2
                
                print(f"[ActionPredictor] VLM Found '{target}' at: L:{pixel_xmin}, T:{pixel_ymin}, R:{pixel_xmax}, B:{pixel_ymax}")
                
                # Crop template and save to memory for NEXT time
                w = pixel_xmax - pixel_xmin
                h = pixel_ymax - pixel_ymin
                if w > 0 and h > 0:
                    new_template = img_cv[pixel_ymin:pixel_ymax, pixel_xmin:pixel_xmax]
                    self.memory[target_key] = {
                        "coords": (center_x, center_y),
                        "template": new_template,
                        "bbox": (pixel_xmin, pixel_ymin, w, h)
                    }
                    # Persist to Atlas for next session
                    if self.memory_agent:
                        context = action.get('app_window', 'Desktop')
                        self.memory_agent.remember_element(context, target, {
                            "coords": [pixel_xmin, pixel_ymin, w, h],
                            "type": "vlm_discovered"
                        }, template=new_template)
                    
                return {"x": center_x, "y": center_y}
        except Exception as e:
            print(f"[ActionPredictor ERROR] Failed to parse VLM output: {vlm_response}. Error: {e}")
            
        # Default fallback
        return {"x": 100, "y": 100}

    def record_outcome(self, action: Dict[str, Any], success: bool):
        """
        Updates memory if an action failed.
        """
        if not success:
             target = action.get('target')
             if target and target in self.memory:
                 print(f"[ActionPredictor] Action failed on '{target}'. Removing from memory.")
                 del self.memory[target]

