with open('example.html', 'r') as f:
    html_content = f.read()

start_tag = "<h1>"
end_tag = "</h1>"
start_index = html_content.find(start_tag) + len(start_tag)
end_index = html_content.find(end_tag)
heading_text = html_content[start_index:end_index]

import json
output = {"heading": heading_text}
with open('output.json', 'w') as f:
    json.dump(output, f)
