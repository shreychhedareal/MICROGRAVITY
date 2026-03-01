import asyncio
import json
import os
from nanobot.agent.tools.browser import BrowserTool

async def test_reddit_bypass():
    print("Testing Anti-Bot Bypass on Reddit...")
    # Initialize with headless mode off so we can see what happens
    browser = BrowserTool(headless=False)
    
    # Action 1: Navigate to Reddit
    print("Action: Navigate to Reddit...")
    nav_res = await browser.execute("navigate", url="https://www.reddit.com/r/technology/")
    nav_data = json.loads(nav_res)
    print(f"Result: {nav_data}")
    
    if nav_data.get("status") == "success":
        # Action 2: Check HTML for CAPTCHA
        print("Action: Take screenshot to verify...")
        await browser.execute("screenshot", path="reddit_bypass_test.png")
        
        print("Action: get_html to check block...")
        html_res = await browser.execute("get_html")
        html_data = json.loads(html_res)
        html_content = html_data.get("html", "")
        
        is_blocked = "We've disabled your request" in html_content or "captcha" in html_content.lower()
        if is_blocked:
            print("FAILURE: We hit a CAPTCHA or block page.")
        else:
            print(f"SUCCESS: Page loaded successfully. HTML length: {len(html_content)}")
            
    # Cleanup
    await browser.execute("close")
    
    # Verify Logs
    if os.path.exists("browser_actions.log"):
        print("\n--- Testing Log Output ---")
        with open("browser_actions.log", "r", encoding="utf-8") as f:
            print(f.read())
    else:
        print("FAILURE: browser_actions.log was not created!")

if __name__ == "__main__":
    asyncio.run(test_reddit_bypass())
