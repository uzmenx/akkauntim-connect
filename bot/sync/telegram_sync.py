import logging
import requests
from bot.config import BotConfig

logger = logging.getLogger(__name__)

class TelegramSync:
    def __init__(self, config: BotConfig):
        self.config = config
        self.enabled = bool(self.config.telegram_bot_token and self.config.telegram_chat_id)
        if not self.enabled:
            logger.info("Telegram notification is disabled (missing token or chat_id).")

    def send_message(self, text: str):
        if not self.enabled:
            return

        url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": self.config.telegram_chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("Telegram ga xabar yuborildi.")
            else:
                logger.warning(f"Telegram ga yuborishda xatolik: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Telegram bilan aloqada xatolik: {e}")

    def send_signal(self, symbol: str, signal: str, confidence: int, sl: float, tp: float, reasoning: str):
        if not self.enabled:
            return

        url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"
        
        # Emoji qoidalari
        if signal.upper() == "BUY":
            signal_emoji = "🟢 BUY"
        elif signal.upper() == "SELL":
            signal_emoji = "🔴 SELL"
        else:
            signal_emoji = f"⚪ {signal}"

        # Xabar matnini tayyorlash
        text = (
            f"🚀 <b>YANGI SIGNAL</b> 🚀\n\n"
            f"💎 <b>Juftlik:</b> #{symbol}\n"
            f"📊 <b>Signal:</b> {signal_emoji}\n"
            f"🎯 <b>Ishonchlilik:</b> {confidence}%\n"
            f"🛡 <b>Stop Loss:</b> {sl} pips\n"
            f"💰 <b>Take Profit:</b> {tp} pips\n\n"
            f"📝 <b>Sabab:</b>\n"
            f"<i>{reasoning}</i>"
        )

        payload = {
            "chat_id": self.config.telegram_chat_id,
            "text": text,
            "parse_mode": "HTML"
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info(f"Telegram ({self.config.telegram_chat_id}) ga signal muvaffaqiyatli yuborildi.")
            else:
                logger.warning(f"Telegram ga yuborishda xatolik: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Telegram bilan aloqada xatolik: {e}")
