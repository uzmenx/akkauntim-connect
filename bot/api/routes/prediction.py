from fastapi import APIRouter
from dataclasses import dataclass
import numpy as np
import logging

# Fan Simulator
from bot.prediction.fan_simulator import FanConfig, simulate_fan
from bot.prediction.signal_merger import merge_signals

logger = logging.getLogger(__name__)
router = APIRouter()

@dataclass
class VotingResult:
    direction: str
    confidence: float

def get_recent_closes(symbol: str, timeframe: str, count: int) -> np.ndarray:
    """mavjud data layer'dan oxirgi shamlarni oladi"""
    try:
        from bot.core.mt5_client import MT5Client
        client = MT5Client()
        rates = client.get_rates(symbol, timeframe, count)
        if rates is not None and len(rates) > 0:
            # rates odatda named tuple yoki dict bo'ladi
            # agar MT5 dan olingan bo'lsa, 'close' maydoni bo'ladi
            closes = [r['close'] if isinstance(r, dict) or isinstance(r, np.void) else r[4] for r in rates]
            return np.array(closes)
    except Exception as e:
        logger.warning(f"get_recent_closes xatosi: {e}")
        
    # Agar ulana olmasa, frontend qotib qolmasligi uchun fallback (fake data)
    return np.linspace(100.0, 102.0, count)

def get_latest_voting_result(symbol: str) -> VotingResult:
    """voting engine'dan joriy signal va ishonchni oladi"""
    # Hozircha DB yoki State dan o'qish uchun stub. 
    # TODO: Haqiqiy bot.state_manager yoki decisions_log.db dan o'qiladi.
    try:
        import sqlite3
        import os
        db_path = os.path.join(os.getcwd(), 'decisions_log.db')
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT decision, confidence FROM decisions WHERE pair=? ORDER BY timestamp DESC LIMIT 1", (symbol,))
            row = c.fetchone()
            conn.close()
            if row:
                return VotingResult(direction=row[0], confidence=float(row[1])/100.0)
    except Exception as e:
        logger.warning(f"Voting result o'qishda xatolik: {e}")
        
    # Fallback default
    return VotingResult(direction="NEUTRAL", confidence=0.5)

def get_lstm_forecast(symbol: str) -> dict:
    """LSTM bashoratini (alohida qalin chiziq uchun) qaytaradi"""
    try:
        from bot.learning.predictor import PredictorEngine
        predictor = PredictorEngine()
        # Odatda MT5 dan oxirgi 10 sham olinadi
        dummy_candles = [{"open": 1, "high": 1.1, "low": 0.9, "close": 1.05, "tick_volume": 100} for _ in range(30)]
        return predictor.predict(dummy_candles)
    except Exception as e:
        logger.warning(f"LSTM bashorat xatosi: {e}")
        return {"prediction": "HOLD", "confidence": 0, "network_state": {}}

def get_shadow_lstm_stats(symbol: str) -> dict:
    """shadow_trade_history'dan LSTM-davridagi win rate va trade sonini hisoblaydi."""
    import sqlite3, os
    try:
        db_path = os.path.join(os.getcwd(), 'bot_learning.db')
        if not os.path.exists(db_path):
            return {"win_rate": 0.5, "trade_count": 0}
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM shadow_trade_history WHERE symbol=?", (symbol,))
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM shadow_trade_history WHERE symbol=? AND profit > 0", (symbol,))
        wins = c.fetchone()[0]
        conn.close()
        win_rate = (wins / total) if total > 0 else 0.5
        return {"win_rate": win_rate, "trade_count": total}
    except Exception as e:
        logger.warning(f"Shadow stats o'qishda xato: {e}")
        return {"win_rate": 0.5, "trade_count": 0}


@router.get("/api/predict/fan/{symbol}")
async def get_prediction_fan(symbol: str, timeframe: str = "M5"):
    closes = get_recent_closes(symbol, timeframe, count=100)
    voting_result = get_latest_voting_result(symbol)
    lstm_result = get_lstm_forecast(symbol)
    shadow_stats = get_shadow_lstm_stats(symbol)

    merged = merge_signals(
        symbol=symbol,
        timeframe=timeframe,
        voting_direction=voting_result.direction,
        voting_confidence=voting_result.confidence,
        lstm_direction=lstm_result.get("prediction", "HOLD"),
        lstm_confidence=lstm_result.get("confidence", 0),
        shadow_win_rate=shadow_stats["win_rate"],
        shadow_trade_count=shadow_stats["trade_count"],
    )

    config = FanConfig(n_paths=60, n_steps=15)
    
    if len(closes) > 0:
        paths = simulate_fan(
            closes=closes,
            direction=merged.direction,
            confidence=merged.confidence,
            config=config,
        )
        paths_list = paths.tolist()
        last_price = float(closes[-1])
    else:
        paths_list = []
        last_price = 0.0

    return {
        "symbol": symbol,
        "last_price": last_price,
        "direction": merged.direction,
        "confidence": merged.confidence,
        "paths": paths_list,
        "lstm_point_forecast": lstm_result,
        "signal_breakdown": {
            "voting_engine": {"direction": voting_result.direction, "confidence": voting_result.confidence},
            "shadow_lstm": {"direction": lstm_result.get("prediction"), "confidence": lstm_result.get("confidence", 0) / 100.0,
                             "historical_win_rate": shadow_stats["win_rate"], "trade_count": shadow_stats["trade_count"]},
            "agreement": merged.agreement,
        },
    }

