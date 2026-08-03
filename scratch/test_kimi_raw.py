import os
import requests

api_key = os.environ.get("KIMI_API_KEY", "sk-KZ2e6fK2Vm2T4xOICJe9etn3989jYmisRKnHtuljocyhX7Z8")
url = "https://api.moonshot.ai/v1/chat/completions"
# Yoki https://api.moonshot.cn/v1/chat/completions bo'lishi mumkin
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
payload = {
    "model": "moonshot-v1-8k",
    "messages": [{"role": "user", "content": "Salom, ishlayapsanmi?"}],
}

# 1-urinish: moonshot-v1-8k
print("Testing moonshot-v1-8k on api.moonshot.cn...")
try:
    r = requests.post("https://api.moonshot.cn/v1/chat/completions", headers=headers, json=payload)
    print(r.json())
except Exception as e:
    print(e)

# 2-urinish: kimi-k3
print("\nTesting kimi-k3 on api.moonshot.ai...")
payload["model"] = "kimi-k3"
try:
    r = requests.post("https://api.moonshot.ai/v1/chat/completions", headers=headers, json=payload)
    print(r.json())
except Exception as e:
    print(e)
