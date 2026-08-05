import json

with open("public/data/chart_XAUUSD_H1.json", "r") as f:
    data = json.load(f)

print("Keys:", data.keys())
print("Candles count:", len(data.get("candles", [])))
overlays = data.get("strategy_overlays", {})
print("Overlays keys:", overlays.keys())
for key, val in overlays.items():
    print(f"Overlay {key} count: {len(val)}")
