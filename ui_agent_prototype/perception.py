import pyautogui
import logging
from PIL import ImageGrab
import os
import time
import base64
import asyncio
from nanobot.providers.litellm_provider import LiteLLMProvider

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PerceptionEngine")

class PerceptionEngine:
    """Handles gathering screen context for the UI/UX Agent."""
    
    def __init__(self, output_dir="temp_vision"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"Created output directory: {self.output_dir}")
        self.screen_width, self.screen_height = pyautogui.size()

    def capture_screenshot(self, region=None):
        """
        Captures the screen or a specific region.
        Region is a tuple: (left, top, width, height)
        Returns the path to the saved image.
        """
        timestamp = int(time.time())
        file_name = f"screenshot_{timestamp}.png"
        file_path = os.path.join(self.output_dir, file_name)
        
        try:
            if region:
                logger.info(f"Capturing region {region}")
                screenshot = ImageGrab.grab(bbox=(region[0], region[1], region[0]+region[2], region[1]+region[3]))
            else:
                logger.info("Capturing full screen")
                screenshot = ImageGrab.grab()
            
            screenshot.save(file_path)
            logger.info(f"Saved screenshot to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return None

    def analyze_with_vision(self, image_path, query="Describe the UI elements on this screen."):
        """
        Uses an LLM (via LiteLLMProvider) to analyze the screenshot based on the query.
        """
        logger.info(f"Performing real semantic analysis of {image_path} with query: '{query}'")
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                
            # Initialize provider (assuming nanobot config/env is present)
            # Utilizing a fast visual model as default
            provider = LiteLLMProvider(default_model="gemini/gemini-2.5-flash")
            
            messages = [
                {"role": "user", "content": [
                    {"type": "text", "text": query},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_string}"}}
                ]}
            ]
            
            response = asyncio.run(provider.chat(messages=messages, max_tokens=1000))
            return {
                "vision_analysis": response.content,
                "resolution": (self.screen_width, self.screen_height),
                "estimated_state": "Vision LLM Analyzed"
            }
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return {"error": str(e)}

if __name__ == "__main__":
    p = PerceptionEngine()
    path = p.capture_screenshot()
    print(f"Captured to: {path}")
    print(f"Basic Analysis: {p.analyze_screen_basic()}")
