import urllib.request
import time

url = "https://khxgspuviykdnlginfsg.supabase.co"
print(f"Requesting {url}...")
start = time.time()
try:
    with urllib.request.urlopen(url, timeout=5) as response:
        html = response.read()
        print(f"Status: {response.status}")
        print(f"Response size: {len(html)}")
except Exception as e:
    print(f"Error: {e}")
print(f"Time taken: {time.time() - start:.2f} seconds")
