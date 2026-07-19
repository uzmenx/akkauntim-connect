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


def fetch_bot_settings() -> dict:
    """Frontend sozlamalarini (symbols, timeframe_major) yuklab olish."""
    if not ENDPOINT or not BOT_SYNC_SECRET or not MT5_LOGIN:
        return {}
    payload = {"mt5_login": MT5_LOGIN, "ping": True}
    try:
        r = requests.post(
            ENDPOINT,
            json=payload,
            headers={"x-bot-secret": BOT_SYNC_SECRET, "Content-Type": "application/json"},
            timeout=10,
        )
        if r.status_code < 300:
            data = r.json()
            return data.get("settings") or {}
        return {}
    except Exception as e:
        print(f"XATO: fetch_bot_settings: {e}")
        return {}


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


def sync_trade_history() -> None:
    if not mt5.initialize():
        return
    # Oxirgi 3 kunlik yopilgan savdolarni olish
    now = datetime.datetime.now(datetime.timezone.utc)
    from_date = now - datetime.timedelta(days=3)
    deals = mt5.history_deals_get(from_date, now)
    
    if deals is None or len(deals) == 0:
        return

    closed_rows = []
    for d in deals:
        # DEAL_ENTRY_OUT (1) yoki DEAL_ENTRY_INOUT (2) bo'lsa pozitsiya yopilgan degani
        if d.entry in [1, 2] and d.symbol:
            # Agar yopish amaliyoti SELL bo'lsa, demak ochiq pozitsiya BUY bo'lgan
            side = "BUY" if d.type == mt5.DEAL_TYPE_SELL else "SELL"
            closed_rows.append({
                "id": d.ticket,          # Unikal ID sifatida deal ticket
                "ticket": d.position_id, # Asosiy pozitsiya ID si
                "symbol": d.symbol,
                "side": side,
                "volume": float(d.volume),
                "open_price": 0.0,       # Aniq olish uchun position tarixi kerak, xozircha 0
                "close_price": float(d.price),
                "profit": float(d.profit),
                "opened_at": datetime.datetime.fromtimestamp(d.time).isoformat(), # Aslida deal.time, opened_at ga vaqtinchalik yozildi
                "closed_at": datetime.datetime.fromtimestamp(d.time).isoformat(),
            })
            
    if closed_rows:
        if _post({"closed_trades": closed_rows}):
            print(f"OK: {len(closed_rows)} ta yopilgan savdo (history) sinxronlandi")


def log_ai_signal(symbol: str, signal: str, confidence: int, reasoning: str = "",
                  stop_loss_pips: float | None = None, take_profit_pips: float | None = None) -> None:
    _post({"ai_signal": {
        "symbol": symbol, "signal": signal, "confidence": confidence,
        "reasoning": reasoning,
        "stop_loss_pips": stop_loss_pips, "take_profit_pips": take_profit_pips,
    }})


def log_claude_cost(cost: float) -> None:
    if _post({"add_claude_cost": cost}):
        print(f"OK: Claude cost loglandi (${cost:.6f})")


def run_sync() -> None:
    sync_bot_status()
    sync_positions()
    sync_trade_history()


if __name__ == "__main__":
    run_sync()
