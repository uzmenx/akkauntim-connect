import re

with open("bot/sync/supabase_sync.py", "r") as f:
    content = f.read()

if "def update_bot_settings" not in content:
    new_method = """
    def update_bot_settings(self, updates: dict) -> None:
        if not self.config.supabase_url or not self.config.supabase_key:
            return
        url = f"{self.config.supabase_url}/rest/v1/bot_settings?mt5_login=eq.{self.config.mt5_login}"
        headers = {
            "apikey": self.config.supabase_key,
            "Authorization": f"Bearer {self.config.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        try:
            requests.patch(url, headers=headers, json=updates, timeout=10)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"update_bot_settings xatolik: {e}")
"""
    content += new_method
    with open("bot/sync/supabase_sync.py", "w") as f:
        f.write(content)
