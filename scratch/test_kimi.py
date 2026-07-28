import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from bot.config import BotConfig
from bot.core.ai_client import AIClient
from dotenv import load_dotenv

load_dotenv()
cfg = BotConfig.load()
print(f"Loaded KIMI_API_KEY: {'Yes' if cfg.kimi_api_key else 'No'}")
client = AIClient(cfg)

print("\n--- Testing Simple Response ---")
try:
    resp = client.get_simple_response("Salom! Sen kimning AIsisan?", max_tokens=50)
    print(f"Response: {resp}")
except Exception as e:
    print(f"Error: {e}")

print("\n--- Testing Decision Request ---")
try:
    decision = client.get_decision("Bu test xabar, faqat {'status': 'ok'} deb json qaytar.", max_tokens=100)
    print(f"Decision: {decision}")
except Exception as e:
    print(f"Error: {e}")
