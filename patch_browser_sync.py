import re

browser_path = r'C:\Users\HP\nanobot\nanobot\agent\tools\browser.py'
with open(browser_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports for webdriver-manager
new_imports = '''import undetected_chromedriver as uc
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service'''

content = re.sub(r'import undetected_chromedriver as uc', new_imports, content)

# Patch _ensure_browser to use Service and ChromeDriverManager
old_init = 'self.driver = uc.Chrome(options=options)'
new_init = '''
                # Proactively ensure driver is synced with installed Chrome version
                driver_path = ChromeDriverManager().install()
                # undetected_chromedriver can use the driver_executable_path directly
                self.driver = uc.Chrome(options=options, driver_executable_path=driver_path)
'''

if old_init in content:
    content = content.replace(old_init, new_init)
    with open(browser_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Patched BrowserTool with ChromeDriverManager')
else:
    print('FAILED: Could not find initialization line in BrowserTool')
