import urllib.request
import json

payload = json.dumps({"prompt": "What beach trips have there been?"}).encode()

req = urllib.request.Request(
    "http://localhost:8000/chat",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urllib.request.urlopen(req) as res:
    body = json.loads(res.read())
    print(body["response"])
