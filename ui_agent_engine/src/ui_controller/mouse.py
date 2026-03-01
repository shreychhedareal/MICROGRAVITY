import pyautogui
import time
import random
from typing import Tuple, Optional
import sys
import os

# Add parent dir to path to find utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.math_utils import generate_human_like_path

# Disable PyAutoGUI's default pause as we handle timing manually for more realism
pyautogui.PAUSE = 0
# Fail-safe feature: moving mouse to a corner aborts the program
pyautogui.FAILSAFE = True

from dataclasses import dataclass, field
from typing import Tuple, Optional, Dict, Any, List

@dataclass
class ActionBlueprint:
    """Defines the parameterized kinematics for a specific mouse/UI action."""
    action_type: str  # 'click', 'double_click', 'drag', 'swipe', 'scrub'
    target_x: int
    target_y: int
    
    # Optional parameters for complex interactions
    source_x: Optional[int] = None
    source_y: Optional[int] = None
    button: str = 'left'
    
    # Kinematics
    easing_func: str = 'linear' # 'linear', 'easeInQuad', 'easeOutQuad', 'easeInOutQuad'
    duration: Optional[float] = None
    hold_duration_ms: int = 0
    exit_velocity_px_s: Optional[float] = None # For kinetic swipes
    axis_lock: Optional[str] = None # 'x' or 'y' for precision scrubbing

class MouseController:
    """
    Controls the mouse with human-like imperfections.
    """
    def __init__(self, base_speed: float = 1.0):
        self.base_speed = base_speed  # Multiplier for movement durations

    def _sleep_random(self, base_time: float, variance: float = 0.2):
        """Sleeps for a random duration around the base_time."""
        sleep_time = max(0.01, random.uniform(base_time * (1 - variance), base_time * (1 + variance)))
        time.sleep(sleep_time)

    def move_to(self, x: int, y: int, duration: Optional[float] = None, human_like: bool = True):
        """
        Moves the mouse to a specific coordinate.
        """
        start_pos = pyautogui.position()
        end_pos = (x, y)
        
        # Distance determines base duration if not provided
        dist = ((end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2)**0.5
        
        if duration is None:
            # Base logic: faster for long distances, slower for short precision movements
            duration_calc = max(0.2, min(1.5, dist / 1500.0))
            duration = duration_calc * self.base_speed * random.uniform(0.8, 1.2)
        
        if human_like and dist > 10: # Only use curve for meaningful distances
            path = generate_human_like_path(start_pos, end_pos)
            
            # Calculate time per step
            steps = len(path)
            time_per_step = duration / steps
            
            for point in path:
                # Add minor jitter to speed
                step_sleep = time_per_step * random.uniform(0.7, 1.3)
                pyautogui.moveTo(point[0], point[1])
                time.sleep(max(0.001, step_sleep))
        else:
            # Linear move with easing for short distances or non-human flag
            pyautogui.moveTo(x, y, duration, pyautogui.easeOutQuad)

    def click(self, button: str = 'left'):
        """Simulates a human-like click (down, short random pause, up)."""
        duration = random.uniform(0.05, 0.15) # Typical human click duration
        pyautogui.mouseDown(button=button)
        time.sleep(duration)
        pyautogui.mouseUp(button=button)

    def double_click(self, button: str = 'left'):
        """Simulates a human double click."""
        self.click(button)
        # Delay between clicks
        self._sleep_random(0.1, 0.05)
        self.click(button)

    def move_and_click(self, x: int, y: int, button: str = 'left', human_like: bool = True):
        """Moves to coordinate and clicks."""
        self.move_to(x, y, human_like=human_like)
        # Brief pause before clicking, as humans often do
        self._sleep_random(0.2)
        self.click(button)

    def drag_to(self, target_x: int, target_y: int, source_x: Optional[int] = None, source_y: Optional[int] = None, button: str = 'left'):
        """
        Drags from current or source position to target position.
        """
        if source_x is not None and source_y is not None:
            self.move_to(source_x, source_y)
            self._sleep_random(0.3)
            
        pyautogui.mouseDown(button=button)
        self._sleep_random(0.2)
        
        # Use move_to for human-like drag path
        self.move_to(target_x, target_y)
        
        self._sleep_random(0.2)
        pyautogui.mouseUp(button=button)

    def scroll(self, clicks: int, direction: str = 'down'):
        """
        Scrolls the mouse wheel. PyAutoGUI handles scroll amounts differently per OS.
        On Windows, a large number (like 100) is often a typical 'click' of the wheel.
        """
        amount = -abs(clicks) if direction == 'down' else abs(clicks)
        
        # Humanize scrolling - don't do it instantly if large amount
        if abs(clicks) > 200:
            chunks = 4
            chunk_size = amount // chunks
            for _ in range(chunks):
                pyautogui.scroll(chunk_size)
                self._sleep_random(0.1)
            # Add remainder
            pyautogui.scroll(amount % chunks)
        else:
            pyautogui.scroll(amount)

    def execute_blueprint(self, blueprint: ActionBlueprint):
        """Executes a complex parameterized action blueprint."""
        
        # 1. Resolve Easing Function
        easing_map = {
            'linear': pyautogui.linear,
            'easeInQuad': pyautogui.easeInQuad,
            'easeOutQuad': pyautogui.easeOutQuad,
            'easeInOutQuad': pyautogui.easeInOutQuad
        }
        easing = easing_map.get(blueprint.easing_func, pyautogui.linear)
        
        # 2. Source Move
        if blueprint.source_x is not None and blueprint.source_y is not None:
            self.move_to(blueprint.source_x, blueprint.source_y, human_like=True)
            self._sleep_random(0.3)
            
        # 3. Apply Axis Lock (Scrubbing)
        cur_x, cur_y = pyautogui.position()
        target_x = blueprint.target_x
        target_y = blueprint.target_y
        
        if blueprint.axis_lock == 'x':
            target_y = cur_y
        elif blueprint.axis_lock == 'y':
            target_x = cur_x
            
        # 4. Execute specific action type kinematics
        if blueprint.action_type == 'click':
            self.move_to(target_x, target_y, duration=blueprint.duration)
            pyautogui.mouseDown(button=blueprint.button)
            if blueprint.hold_duration_ms > 0:
                time.sleep(blueprint.hold_duration_ms / 1000.0)
            else:
                self._sleep_random(0.1)
            pyautogui.mouseUp(button=blueprint.button)
            
        elif blueprint.action_type == 'double_click':
            self.move_to(target_x, target_y, duration=blueprint.duration)
            self.double_click(button=blueprint.button)
            
        elif blueprint.action_type in ['drag', 'scrub', 'swipe']:
            pyautogui.mouseDown(button=blueprint.button)
            self._sleep_random(0.2)
            
            # Non-linear dragging with calculated easing
            dist = ((target_x - cur_x)**2 + (target_y - cur_y)**2)**0.5
            exec_duration = blueprint.duration
            if exec_duration is None:
                if blueprint.action_type == 'swipe' and blueprint.exit_velocity_px_s:
                    # Time = Distance / Velocity
                    exec_duration = dist / blueprint.exit_velocity_px_s
                else:
                    exec_duration = max(0.2, dist / 1000.0)
                    
            pyautogui.moveTo(target_x, target_y, duration=exec_duration, tween=easing)
            
            if blueprint.hold_duration_ms > 0:
                time.sleep(blueprint.hold_duration_ms / 1000.0)
                
            pyautogui.mouseUp(button=blueprint.button)
