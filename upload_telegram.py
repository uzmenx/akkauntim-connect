import os
import requests
from dotenv import load_dotenv
import time

def send_to_telegram():
    load_dotenv()
    
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("[XATOLIK] Telegram bot token yoki chat ID topilmadi.")
        return
        
    zip_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_migration_package.zip")
    
    if not os.path.exists(zip_path):
        print(f"[XATOLIK] {zip_path} topilmadi.")
        return
        
    file_size = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"Telegram orqali fayl yuborilmoqda... Hajmi: {file_size:.2f} MB")
    print("(Katta fayl bo'lganligi sababli biroz vaqt olishi mumkin)")
    
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    
    try:
        with open(zip_path, 'rb') as f:
            response = requests.post(
                url, 
                data={'chat_id': chat_id, 'caption': '📦 Bot Migratsiya Paketi (Zaxira)\n\nFleshka yo\'qolib qolgan taqdirda ushbu fayldan foydalaning.'},
                files={'document': f}
            )
            
        if response.status_code == 200:
            print("[MUVAFFAQIYATLI] Zaxira muvaffaqiyatli Telegramingizga yuborildi!")
        else:
            print(f"[XATOLIK] Telegramga yuborish muvaffaqiyatsiz bo'ldi. Kod: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"[XATOLIK] Tarmoq xatosi: {e}")

if __name__ == "__main__":
    send_to_telegram()
