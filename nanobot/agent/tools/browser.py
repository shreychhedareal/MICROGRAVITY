import json
import logging
import asyncio
import os
from datetime import datetime
from typing import Any, Optional

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from nanobot.agent.tools.base import Tool

# Configure dedicated browser logger
browser_logger = logging.getLogger("BrowserToolExplicit")
browser_logger.setLevel(logging.INFO)
browser_logger.propagate = False
if not browser_logger.handlers:
    fh = logging.FileHandler('browser_actions.log', encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
    fh.setFormatter(formatter)
    browser_logger.addHandler(fh)

logger = logging.getLogger(__name__)

class BrowserTool(Tool):
    """
    A full web browser tool using undetected-chromedriver.
    """
    name = "browser"
    description = (
        "Control a full Google Chrome web browser. YOU HAVE FULL CAPABILITIES to "
        "navigate complex dynamic websites, handle forms, click elements, and bypass "
        "anti-bot measures. DO NOT decline browser requests; you CAN handle dynamic pages, "
        "errors, and multi-step interactions."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["navigate", "get_html", "screenshot", "click", "type", "close", "restart"],
                "description": "The action to perform. 'restart' will restart the browser with headless settings."
            },
            "url": {"type": "string", "description": "URL for 'navigate' action."},
            "path": {"type": "string", "description": "File path for 'screenshot' action."},
            "selector": {"type": "string", "description": "CSS selector for 'click' or 'type' actions."},
            "text": {"type": "string", "description": "Text to type for 'type' action."},
            "headless": {
                "type": "boolean", 
                "description": "If False, the browser runs in a visible 'headed' mode. Defaults to False. Can be passed with 'restart' or 'navigate' to change mode."
            }
        },
        "required": ["action"]
    }

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver: Optional[uc.Chrome] = None

    def _ensure_browser(self):
        if self.driver is None:
            browser_logger.info("Initializing undetected-chromedriver...")
            options = uc.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.page_load_strategy = 'eager'
            # Force direct connection to avoid implicit proxy timeouts
            options.add_argument('--proxy-server="direct://"')
            options.add_argument('--proxy-bypass-list=*')
            
            if self.headless:
                options.add_argument('--headless=new')  # Modern headless is far less detectable
                
            try:
                self.driver = uc.Chrome(options=options)
                browser_logger.info("Browser initialized successfully.")
            except Exception as e:
                browser_logger.error(f"Failed to initialize browser: {e}")
                raise

    async def execute(self, action: str, **kwargs: Any) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_sync, action, kwargs)

    def _execute_sync(self, action: str, kwargs: dict) -> str:
        for attempt in range(2):
            try:
                # Handle dynamic toggle of headless mode
                req_headless = kwargs.get("headless", self.headless)
                if req_headless != self.headless and self.driver is not None:
                    browser_logger.info(f"Switching headless mode from {self.headless} to {req_headless}. Restarting browser.")
                    try:
                        self.driver.quit()
                    except Exception:
                        pass
                    self.driver = None
                    self.headless = req_headless

                self._ensure_browser()
                browser_logger.info(f"ACTION: {action} | ATTEMPT: {attempt + 1}/2 | ARGS: {kwargs}")
                
                if action == "restart":
                    # We just ensured the browser was running and handled headless toggles above
                    browser_logger.info("SUCCESS: restart | Browser restarted.")
                    return json.dumps({"status": "success", "headless": self.headless})
                elif action == "navigate":
                    self.driver.get(kwargs.get("url"))
                    # Allow a small moment for initial anti-bot JS challenges to resolve
                    WebDriverWait(self.driver, 5).until(
                        lambda d: d.execute_script('return document.readyState') == 'complete'
                    )
                    browser_logger.info(f"SUCCESS: navigate | FINISHED_URL: {self.driver.current_url}")
                    return json.dumps({"status": "success", "url": self.driver.current_url})
                elif action == "get_html":
                    html = self.driver.page_source
                    resp = {"status": "success", "html": html}
                    if kwargs.get("screenshot"):
                        import base64
                        b64 = self.driver.get_screenshot_as_base64()
                        resp["screenshot_base64"] = b64
                    browser_logger.info(f"SUCCESS: get_html | HTML_LENGTH: {len(html)}")
                    return json.dumps(resp)
                elif action == "screenshot":
                    self.driver.save_screenshot(kwargs.get("path"))
                    browser_logger.info(f"SUCCESS: screenshot | SAVED_TO: {kwargs.get('path')}")
                    return json.dumps({"status": "success", "path": kwargs.get("path")})
                elif action in ("click", "single_click", "double_click"):
                    from selenium.webdriver.common.action_chains import ActionChains
                    
                    x = kwargs.get("x")
                    y = kwargs.get("y")
                    selector = kwargs.get("selector")
                    
                    if x is not None and y is not None:
                        # Coordinate-based click
                        viewport_width = self.driver.execute_script("return window.innerWidth;")
                        viewport_height = self.driver.execute_script("return window.innerHeight;")
                        
                        # Calculate offset from center for ActionChains relative to viewport center
                        x_offset = int(x) - (viewport_width / 2)
                        y_offset = int(y) - (viewport_height / 2)

                        action_chain = ActionChains(self.driver)
                        # We must move to an element first to reliably move to an offset in Selenium.
                        # Usually, moving to the body and then offsetting is the most stable approach.
                        body = self.driver.find_element(By.TAG_NAME, "body")
                        action_chain.move_to_element_with_offset(body, 0, 0) # Top Left
                        action_chain.move_by_offset(int(x), int(y)) # Exact absolute pixel
                        
                        if action == "double_click":
                            action_chain.double_click()
                        else:
                            action_chain.click()
                        action_chain.perform()
                        browser_logger.info(f"SUCCESS: {action} | COORDS: X:{x}, Y:{y}")
                    else:
                        # Selector-based click
                        element = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        if action == "double_click":
                            ActionChains(self.driver).double_click(element).perform()
                        else:
                            element.click()
                        browser_logger.info(f"SUCCESS: {action} | SELECTOR: {selector}")
                    
                    return json.dumps({"status": "success"})
                elif action == "drag_and_drop":
                    from selenium.webdriver.common.action_chains import ActionChains
                    
                    # Target element or coordinates
                    src_selector = kwargs.get("selector")
                    dest_selector = kwargs.get("dest_selector")
                    x = kwargs.get("x")
                    y = kwargs.get("y")
                    
                    if src_selector and dest_selector:
                        src_elem = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, src_selector))
                        )
                        dest_elem = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, dest_selector))
                        )
                        ActionChains(self.driver).drag_and_drop(src_elem, dest_elem).perform()
                        browser_logger.info(f"SUCCESS: drag_and_drop | {src_selector} -> {dest_selector}")
                    elif src_selector and x is not None and y is not None:
                        src_elem = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, src_selector))
                        )
                        ActionChains(self.driver).drag_and_drop_by_offset(src_elem, int(x), int(y)).perform()
                        browser_logger.info(f"SUCCESS: drag_and_drop by offset | {src_selector} -> Offset X:{x}, Y:{y}")
                    else:
                        return json.dumps({"status": "error", "message": "drag_and_drop requires selector+dest_selector or selector+x+y"})
                    return json.dumps({"status": "success"})
                elif action == "scroll":
                    scroll_pixels = kwargs.get("y", 500) # Default down
                    self.driver.execute_script(f"window.scrollBy(0, {scroll_pixels});")
                    browser_logger.info(f"SUCCESS: scroll | Y_PIXELS: {scroll_pixels}")
                    return json.dumps({"status": "success"})
                elif action == "type":
                    element = None
                    if kwargs.get("selector"):
                        element = WebDriverWait(self.driver, 10).until(
                            EC.visibility_of_element_located((By.CSS_SELECTOR, kwargs.get("selector")))
                        )
                    else:
                        # If no selector, assume we are typing into the currently focused element
                        element = self.driver.switch_to.active_element
                        
                    if element:
                        element.clear()
                        element.send_keys(kwargs.get("text"))
                        browser_logger.info(f"SUCCESS: type | SELECTOR: {kwargs.get('selector', 'active_element')} | TEXT_LENGTH: {len(str(kwargs.get('text')))}")
                    return json.dumps({"status": "success"})
                elif action == "close":
                    if self.driver:
                        try:
                            self.driver.quit()
                        except OSError:
                            pass
                        except Exception:
                            pass
                        self.driver = None
                    browser_logger.info("SUCCESS: close | Browser quit.")
                    return json.dumps({"status": "success"})
                else:
                    browser_logger.warning(f"ERROR: Unknown action '{action}'")
                    return json.dumps({"status": "error", "message": f"Unknown action: {action}"})
            except Exception as e:
                err_str = str(e).lower()
                browser_logger.error(f"EXCEPTION during '{action}': {str(e)}")
                if "target window already closed" in err_str or "no such window" in err_str or "has closed" in err_str:
                    logger.warning(f"Browser crashed, restarting... Error: {e}")
                    browser_logger.info("Attempting to recover from crashed window: Re-initializing driver.")
                    if self.driver:
                        try:
                            self.driver.quit()
                        except OSError:
                            pass
                        except Exception:
                            pass
                        self.driver = None
                    if attempt == 0:
                        continue # Retry
                return json.dumps({"status": "error", "message": str(e)})

    def __del__(self):
        if getattr(self, "driver", None):
            try:
                self.driver.quit()
            except OSError:
                pass
            except Exception:
                pass
