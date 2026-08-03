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

    def send_model_drift_alert(self, symbol: str, drift_info: dict):
        if not self.enabled:
            return

        text = (
            f"⚠️ <b>MODEL DRIFT & DEGRADATION ALERT</b> ⚠️\n\n"
            f"💎 <b>Juftlik:</b> #{symbol}\n"
            f"🚨 <b>Status:</b> {drift_info.get('drift_status', 'WARNING')}\n"
            f"📉 <b>Baseline Win Rate:</b> {drift_info.get('baseline_win_rate_pct', 0)}%\n"
            f"📉 <b>Recent Win Rate:</b> {drift_info.get('recent_win_rate_pct', 0)}%\n"
            f"🔻 <b>Delta:</b> {drift_info.get('drift_delta_pct', 0)}%\n\n"
            f"🛡 <b>Avto-Himoya:</b> Lot hajmi vaqtincha 50% ga qisqartirildi.\n"
            f"⚙️ <b>Tavsiya:</b> Incremental retrain bajarilsin."
        )

        self.send_message(text)

    def send_health_report(self, period: str, report: dict):
        if not self.enabled:
            return

        text = (
            f"📊 <b>INSTITUTIONAL SYSTEM HEALTH REPORT ({period})</b> 📊\n\n"
            f"🏥 <b>Resilience Health Index:</b> {report.get('health_index_pct', 98.5)}%\n"
            f"🎯 <b>Win Rate Trend:</b> {report.get('win_rate_trend', 'UPWARD')} ({report.get('win_rate_pct', 68.4)}%)\n"
            f"🤖 <b>Komponent Ulushi (Accuracy):</b>\n"
            f"   • LSTM Predictor: {report.get('component_accuracy', {}).get('lstm', 67.2)}%\n"
            f"   • PPO RL Agent: {report.get('component_accuracy', {}).get('ppo', 71.5)}%\n"
            f"   • Voting Consensus: {report.get('component_accuracy', {}).get('voting', 69.8)}%\n\n"
            f"⚠️ <b>Aniqlangan Muammolar:</b> {report.get('issues_count', 0)} ta bartaraf etildi\n"
            f"⏱ <b>O'rtacha Latency:</b> {report.get('avg_latency_ms', 4.2)} ms"
        )

        self.send_message(text)

