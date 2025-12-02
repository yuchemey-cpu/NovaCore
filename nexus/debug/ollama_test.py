import requests

ENDPOINTS = [
    "http://127.0.0.1:11434/api/generate",
    "http://127.0.0.1:11434/generate",
    "http://127.0.0.1:11434/api/chat",
    "http://127.0.0.1:11434/chat",
]

prompt = """
### SYSTEM ###
You are Nova. You are 25 years old.

### USER ###
How old are you?

### ASSISTANT ###
"""

for url in ENDPOINTS:
    print("\nTesting:", url)
    try:
        resp = requests.post(url, json={
            "model": "phi3.1:latest",
            "prompt": prompt,
            "stream": False
        }, timeout=10)
        print(resp.status_code, resp.text[:300])
    except Exception as e:
        print("ERROR:", e)
