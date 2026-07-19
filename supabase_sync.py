"""
Python bot -> Lovable Cloud sync via Edge Function.

Bot service_role key olmaydi. Buning o'rniga HTTPS orqali `bot-sync` edge
funksiyasiga POST qilamiz. Shared secret `BOT_SYNC_SECRET` env orqali.

Environment variables:
  SUPABASE_URL           - Cloud project URL (from Lovable Cloud .env)
  BOT_SYNC_SECRET        - shared secret set in Cloud project
  MT5_LOGIN              - the MT5 account number this bot instance controls
                           (must match the login the user signed up with in the panel)
"""
import os
import datetime
import requests
import MetaTrader5 as mt5
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL")
BOT_SYNC_SECRET = os.environ.get("BOT_SYNC_SECRET", "")
MT5_LOGIN = os.environ.get("MT5_LOGIN", "")

ENDPOINT = f"{SUPABASE_URL}/functions/v1/bot-sync" if SUPABASE_URL else None


def _post(payload: dict) -> bool:
    if not ENDPOINT or not BOT_SYNC_SECRET or not MT5_LOGIN:
        print("supabase_sync: SUPABASE_URL / BOT_SYNC_SECRET / MT5_LOGIN kerak")
        return False
    payload = {"mt5_login": MT5_LOGIN, **payload}
    try:
        r = requests.post(
            ENDPOINT,
            json=payload,
            headers={"x-bot-secret": BOT_SYNC_SECRET, "Content-Type": "application/json"},
            timeout=15,
        )
        if r.status_code >= 300:
            print(f"XATO: bot-sync {r.status_code}: {r.text}")
            return False
        return True
    except Exception as e:
        print(f"XATO: bot-sync POST: {e}")
        return False


def sync_bot_status(is_running: bool = True, message: str = "Bot is running") -> None:
    if not mt5.initialize():
        print("sync_bot_status: MT5 ga ulanib bo'lmadi")
        return
    info = mt5.account_info()
    if info is None:
        print("sync_bot_status: hisob ma'lumotlari yo'q")
        return
    ok = _post({
        "status": {
            "is_running": is_running,
            "message": message,
            "account_equity": info.equity,
            "account_balance": info.balance,
            "account_currency": info.currency,
        }
    })
    if ok:
        print(f"OK: bot_status sinxronlandi (balans={info.balance})")


def sync_positions() -> None:
    if not mt5.initialize():
        return
    positions = mt5.positions_get() or []
    rows = []
    for p in positions:
        rows.append({
            "id": int(p.ticket),
            "symbol": p.symbol,
            "side": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
            "volume": float(p.volume),
            "open_price": float(p.price_open),
            "profit": float(p.profit),
            "opened_at": datetime.datetime.fromtimestamp(p.time).isoformat(),
        })
    if _post({"positions": rows}):
        print(f"OK: {len(rows)} ta pozitsiya sinxronlandi")


def log_ai_signal(symbol: str, signal: str, confidence: int, reasoning: str = "",
                  stop_loss_pips: float | None = None, take_profit_pips: float | None = None) -> None:
    _post({"ai_signal": {
        "symbol": symbol, "signal": signal, "confidence": confidence,
        "reasoning": reasoning,
        "stop_loss_pips": stop_loss_pips, "take_profit_pips": take_profit_pips,
    }})


def run_sync() -> None:
    sync_bot_status()
    sync_positions()


if __name__ == "__main__":
    run_sync()
