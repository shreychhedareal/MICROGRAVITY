import asyncio
import json
from nanobot.agent.tools.browser import BrowserTool

async def main():
    print("Initializing BrowserTool...")
    browser = BrowserTool(headless=False)
    
    print("Navigating to example.com...")
    nav_res = await browser.execute("navigate", url="https://example.com")
    print(f"Navigate Response: {nav_res}")
    
    try:
        nav_data = json.loads(nav_res)
        if nav_data.get("status") == "success":
            print("Taking a screenshot...")
            shoot_res = await browser.execute("screenshot", path="example_screenshot.png")
            print(f"Screenshot Response: {shoot_res}")
            
            print("Getting HTML length...")
            html_res = await browser.execute("get_html")
            html_data = json.loads(html_res)
            print(f"HTML length: {len(html_data.get('html', ''))}")
    finally:
        print("Closing browser...")
        await browser.execute("close")
        print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
