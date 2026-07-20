import time
import logging
from trading_bot_step6 import run_smart_bot
from ai_analysis import load_env, load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def main():
    load_env()  # .env faylini yuklaymiz
    interval_minutes = 5
    while True:
        try:
            # Har bir siklda yangi konfiguratsiyani o'qiymiz
            config = load_config()
            trading_config = config.get("trading", {})
            symbols = trading_config.get("symbols", ["EURUSD"])
            interval_minutes = trading_config.get("loop_interval_minutes", 5)
            
            for symbol in symbols:
                logging.info(f"--- [{symbol}] uchun tahlil boshlandi ---")
                run_smart_bot(symbol)
                logging.info(f"--- [{symbol}] uchun tahlil tugadi ---")
            
            logging.info(f"Barcha juftliklar tekshirildi. Keyingi tsiklgacha {interval_minutes} daqiqa kutilmoqda...")
        except Exception as e:
            logging.error(f"Asosiy siklda xatolik yuz berdi: {e}")
            
        # Kutiladigan vaqt (soniyalarda)
        time.sleep(interval_minutes * 60)

if __name__ == "__main__":
    main()
