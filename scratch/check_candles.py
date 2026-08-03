import os
import requests
from dotenv import load_dotenv

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_PUBLISHABLE_KEY")

if not supabase_url or not supabase_key:
    print("Error: SUPABASE_URL or SUPABASE_PUBLISHABLE_KEY not found in .env")
    exit(1)

# Let's request the candles count
headers = {
    "apikey": supabase_key,
    "Authorization": f"Bearer {supabase_key}"
}

# Fetch candles count
url = f"{supabase_url}/rest/v1/candles?select=count"
r = requests.get(url, headers=headers)
print("Candles table count response status:", r.status_code)
print("Response text:", r.text)

# Fetch user settings to see if the user is registered
url_settings = f"{supabase_url}/rest/v1/bot_settings?select=*"
r_settings = requests.get(url_settings, headers=headers)
print("\nBot settings response status:", r_settings.status_code)
print("Response data:", r_settings.text[:500])
