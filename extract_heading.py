
import json
from bs4 import BeautifulSoup

html_content = """<html lang="en"><head><title>Example Domain</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{background:#eee;width:60vw;margin:15vh auto;font-family:system-ui,sans-serif}h1{font-size:1.5em}div{opacity:0.8}a:link,a:visited{color:#348}</style></head><body><div><h1>Example Domain</h1><p>This domain is for use in documentation examples without needing permission. Avoid use in operations.</p><p><a href="https://iana.org/domains/example">Learn more</a></p></div>
</body></html>"""

soup = BeautifulSoup(html_content, 'html.parser')
heading_text = soup.find('h1').get_text()

output = json.dumps({"heading": heading_text})

with open("output.json", "w") as f:
    f.write(output)
