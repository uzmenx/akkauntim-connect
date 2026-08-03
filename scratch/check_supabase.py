import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("VITE_SUPABASE_URL")
anon_key = os.environ.get("VITE_SUPABASE_PUBLISHABLE_KEY")

if not url or not anon_key:
    print("VITE_SUPABASE_URL or VITE_SUPABASE_PUBLISHABLE_KEY missing")
    exit(1)

# Fetch one row from bot_status
headers = {
    "apikey": anon_key,
    "Authorization": f"Bearer {anon_key}"
}
res = requests.get(f"{url}/rest/v1/bot_status?limit=1", headers=headers)
print("Status code:", res.status_code)
print("Response text:", res.text)
