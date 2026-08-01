import os
import time
import subprocess
import logging
import sys
import requests
from dotenv import load_dotenv

# Konfiguratsiya
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL", os.environ.get("VITE_SUPABASE_URL", ""))
SUPABASE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY", os.environ.get("VITE_SUPABASE_PUBLISHABLE_KEY", ""))
POLL_INTERVAL = 5  # soniyada

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] MANAGER: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Manager")

def get_is_running_from_supabase() -> bool:
    """Supabase'dan bot holatini tekshiradi. Agar ulanishda xatolik bo'lsa True qaytaradi (xavfsizlik uchun ishlayversin)."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return True # Agar sozlanmagan bo'lsa doim ishlasin
    
    url = f"{SUPABASE_URL}/rest/v1/bot_status?select=is_running&limit=1"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data and len(data) > 0:
                # Bazada is_running maydoni true/false
                return bool(data[0].get("is_running", True))
            else:
                # Agar ma'lumot yo'q bo'lsa, odatiy holatda ishlaydi
                return True
        else:
            logger.debug(f"Supabase'dan status olishda xatolik: {r.status_code}")
    except Exception as e:
        logger.debug(f"Supabase bilan aloqa xatosi: {e}")
        
    return True

def main():
    logger.info("Bot Manager ishga tushdi. Supabase kuzatilmoqda...")
    bot_process = None

    while True:
        is_running = get_is_running_from_supabase()
        
        # Holatni tekshiramiz: jarayon ishlab turibdimi?
        process_alive = False
        if bot_process is not None:
            if bot_process.poll() is None:
                process_alive = True
            else:
                # Jarayon o'z-o'zidan o'chib qolgan
                process_alive = False
                logger.warning(f"Bot jarayoni kutilmaganda yopildi. Chiqish kodi: {bot_process.returncode}")
                bot_process = None
        
        # Mantiq
        if is_running and not process_alive:
            logger.info("Bot ishga tushirilmoqda (run_bot.py)...")
            bot_process = subprocess.Popen([sys.executable, "run_bot.py"])
            
        elif not is_running and process_alive:
            logger.info("Bot veb-ilovadan to'xtatildi. Jarayon yopilmoqda...")
            bot_process.terminate()
            try:
                bot_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                bot_process.kill()
            bot_process = None
            logger.info("Bot muvaffaqiyatli to'xtatildi.")
            
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Manager to'xtatildi (Ctrl+C).")
        sys.exit(0)
