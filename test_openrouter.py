import os
import requests
import json
def load_env():
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")
load_env()
api_key = os.environ.get("OPENROUTER_API_KEY")
print(f"Key loaded: {'Yes' if api_key else 'No'}")
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
payload = {
    "model": "deepseek/deepseek-chat",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
}
resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
print(resp.status_code)
print(resp.text)
