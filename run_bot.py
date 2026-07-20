import time
import logging
from trading_bot_step6 import run_smart_bot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def main():
    symbol = "EURUSD"
    interval_minutes = 5
    logging.info(f"Bot ishga tushirildi. Har {interval_minutes} daqiqada {symbol} uchun tahlil qilinadi va savdo holati tekshiriladi.")
    
    while True:
        try:
            logging.info("Tahlil boshlandi...")
            run_smart_bot(symbol)
            logging.info(f"Tahlil tugadi. Keyingi tekshiruvgacha {interval_minutes} daqiqa kutilmoqda...")
        except Exception as e:
            logging.error(f"Xatolik yuz berdi: {e}")
            
        # Kutiladigan vaqt (soniyalarda)
        time.sleep(interval_minutes * 60)

if __name__ == "__main__":
    main()
