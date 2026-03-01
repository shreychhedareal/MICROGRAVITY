import pyautogui
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("UIActionController")

# PyAutoGUI settings
pyautogui.FAILSAFE = True  # Move mouse to a corner to abort
pyautogui.PAUSE = 0.5      # Default delay after each PyAutoGUI call

class ActionController:
    """Handles direct physical interaction with the host UI."""
    
    def __init__(self):
        logger.info("Initializing UI Action Controller")
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"Screen resolution detected: {self.screen_width}x{self.screen_height}")

    def validate_coordinates(self, x, y):
        """Ensure coordinates are within screen bounds."""
        if not (0 <= x <= self.screen_width and 0 <= y <= self.screen_height):
            logger.warning(f"Coordinates ({x}, {y}) are out of bounds. Clamping to screen edges.")
            x = max(0, min(x, self.screen_width))
            y = max(0, min(y, self.screen_height))
        return x, y

    def move_mouse(self, x, y, duration=0.5):
        """Moves mouse to specific coordinates gracefully."""
        x, y = self.validate_coordinates(x, y)
        logger.info(f"Moving mouse to ({x}, {y}) over {duration}s")
        pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeInOutQuad)

    def single_click(self, x=None, y=None, button='left'):
        """Performs a single click at current or specified coordinates."""
        if x is not None and y is not None:
             self.move_mouse(x, y, duration=0.2)
        logger.info(f"Executing single {button} click at current position")
        pyautogui.click(button=button)

    def double_click(self, x=None, y=None, button='left'):
        """Performs a double click."""
        if x is not None and y is not None:
             self.move_mouse(x, y, duration=0.2)
        logger.info(f"Executing double {button} click at current position")
        pyautogui.doubleClick(button=button)
        
    def multiple_clicks(self, clicks=3, x=None, y=None, button='left', interval=0.1):
        """Performs multiple consecutive clicks."""
        if x is not None and y is not None:
            self.move_mouse(x, y, duration=0.2)
        logger.info(f"Executing {clicks} {button} clicks at current position with {interval}s interval")
        pyautogui.click(clicks=clicks, interval=interval, button=button)

    def drag(self, start_x, start_y, end_x, end_y, duration=1.0, button='left'):
        """Clicks and drags from one point to another."""
        self.move_mouse(start_x, start_y, duration=0.2)
        logger.info(f"Dragging {button} from ({start_x}, {start_y}) to ({end_x}, {end_y}) over {duration}s")
        end_x, end_y = self.validate_coordinates(end_x, end_y)
        pyautogui.dragTo(end_x, end_y, duration=duration, button=button)

    def scroll(self, amount, x=None, y=None):
        """Scrolls the mouse wheel. Positive amount scrolls up, negative down."""
        if x is not None and y is not None:
             self.move_mouse(x, y, duration=0.2)
        direction = "up" if amount > 0 else "down"
        logger.info(f"Scrolling {direction} by {abs(amount)} units")
        pyautogui.scroll(amount)

    def type_text(self, text, interval=0.05):
        """Types out a string of text like a human."""
        logger.info(f"Typing text: '{text}' (hidden for security in real logs, but shown here for debug)")
        pyautogui.write(text, interval=interval)

    def press_key(self, key):
        """Presses a specific keyboard key (e.g., 'enter', 'tab', 'shift')."""
        logger.info(f"Pressing key: {key}")
        pyautogui.press(key)
        
    def hotkey(self, *keys):
        """Presses a combination of keys (e.g., 'ctrl', 'c')."""
        logger.info(f"Pressing hotkey: {' + '.join(keys)}")
        pyautogui.hotkey(*keys)

if __name__ == "__main__":
    # Simple test sequence if run directly
    print("Testing ActionController in 3 seconds. DO NOT move mouse.")
    time.sleep(3)
    ac = ActionController()
    width, height = ac.screen_width, ac.screen_height
    # Move to center
    ac.move_mouse(width // 2, height // 2)
    ac.scroll(-100) # Scroll down a bit
    print("Test complete.")
