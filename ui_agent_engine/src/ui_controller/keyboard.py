import pyautogui
import time
import random

# Disable PyAutoGUI's default pause as we handle timing manually
pyautogui.PAUSE = 0

class KeyboardController:
    """
    Controls the keyboard with human-like typing speeds and errors.
    """
    def __init__(self, wpm: int = 60, error_rate: float = 0.02):
        """
        Args:
            wpm: Words per minute target
            error_rate: Probability of making a typo (not implemented yet, but for future use)
        """
        self.wpm = wpm
        self.error_rate = error_rate
        # Calculate base delay per character based on wpm
        # Assuming average word is 5 characters + 1 space
        chars_per_min = wpm * 6
        self.base_delay = 60.0 / chars_per_min if chars_per_min > 0 else 0.1

    def _sleep_random(self, base_time: float, variance: float = 0.3):
        """Sleeps for a random duration around the base_time."""
        sleep_time = max(0.01, random.uniform(base_time * (1 - variance), base_time * (1 + variance)))
        time.sleep(sleep_time)

    def type_text(self, text: str):
        """
        Types a string of text with human-like delays between characters.
        """
        for char in text:
            # Add slight variance per character
            char_delay = self.base_delay * random.uniform(0.7, 1.5)
            
            # Additional pause for punctuation or space
            if char in [' ', '.', ',', '!', '?', '\n']:
                char_delay *= random.uniform(1.2, 2.5)
            
            pyautogui.write(char)
            time.sleep(char_delay)

    def press_key(self, key: str, presses: int = 1):
        """
        Presses a specific key (e.g., 'enter', 'tab', 'ctrl').
        """
        for _ in range(presses):
            pyautogui.press(key)
            self._sleep_random(0.1)

    def hotkey(self, *keys):
        """
        Simulates holding down multiple keys (e.g., ctrl+c).
        """
        # Small delay before action
        self._sleep_random(0.2)
        pyautogui.hotkey(*keys)
        # Small delay after action
        self._sleep_random(0.1)
