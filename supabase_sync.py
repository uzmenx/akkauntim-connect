"""
Python bot -> Lovable Cloud sync via Edge Function.

Har 5 soniyada MT5 dan status/positions/pending_orders/history olib,
Cloud'ga POST qiladi.

Env:
  SUPABASE_URL, BOT_SYNC_SECRET, MT5_LOGIN
"""
import os
import time
import datetime
import requests
import MetaTrader5 as mt5
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL")
BOT_SYNC_SECRET = os.environ.get("BOT_SYNC_SECRET", "")
MT5_LOGIN = os.environ.get("MT5_LOGIN", "")
ENDPOINT = f"{SUPABASE_URL}/functions/v1/bot-sync" if SUPABASE_URL else None


def _post(payload: dict) -> dict | None:
    if not ENDPOINT or not BOT_SYNC_SECRET or not MT5_LOGIN:
        print("supabase_sync: SUPABASE_URL / BOT_SYNC_SECRET / MT5_LOGIN kerak")
        return None
    payload = {"mt5_login": MT5_LOGIN, **payload}
    try:
        r = requests.post(
            ENDPOINT, json=payload,
            headers={"x-bot-secret": BOT_SYNC_SECRET, "Content-Type": "application/json"},
            timeout=15,
        )
        if r.status_code >= 300:
            print(f"XATO: bot-sync {r.status_code}: {r.text}")
            return None
        return r.json()
    except Exception as e:
        print(f"XATO: bot-sync POST: {e}")
        return None


def fetch_bot_settings() -> dict:
    res = _post({"ping": True})
    return (res or {}).get("settings") or {}


def _order_type_name(t: int) -> str:
    return {
        mt5.ORDER_TYPE_BUY_LIMIT: "buy_limit",
        mt5.ORDER_TYPE_SELL_LIMIT: "sell_limit",
        mt5.ORDER_TYPE_BUY_STOP: "buy_stop",
        mt5.ORDER_TYPE_SELL_STOP: "sell_stop",
        mt5.ORDER_TYPE_BUY_STOP_LIMIT: "buy_stop_limit",
        mt5.ORDER_TYPE_SELL_STOP_LIMIT: "sell_stop_limit",
    }.get(t, "unknown")


def sync_all(is_running: bool = True, message: str = "Bot is running") -> None:
    """Bir POST bilan status + positions + pending_orders + history yuboradi."""
    if not mt5.initialize():
        print("MT5 ga ulanib bo'lmadi")
        return
    info = mt5.account_info()
    if info is None:
        print("Hisob ma'lumotlari yo'q")
        return

    # Positions
    positions = mt5.positions_get() or []
    pos_rows = []
    for p in positions:
        pos_rows.append({
            "ticket": int(p.ticket),
            "symbol": p.symbol,
            "side": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
            "volume": float(p.volume),
            "open_price": float(p.price_open),
            "current_price": float(p.price_current),
            "stop_loss": float(p.sl) if p.sl else None,
            "take_profit": float(p.tp) if p.tp else None,
            "profit": float(p.profit),
            "opened_at": datetime.datetime.fromtimestamp(p.time).isoformat(),
        })

    # Pending orders
    orders = mt5.orders_get() or []
    pending_rows = []
    for o in orders:
        pending_rows.append({
            "ticket": int(o.ticket),
            "symbol": o.symbol,
            "type": _order_type_name(o.type),
            "volume": float(o.volume_current),
            "price": float(o.price_open),
            "stop_loss": float(o.sl) if o.sl else None,
            "take_profit": float(o.tp) if o.tp else None,
        })

    # Closed history (oxirgi 7 kun)
    now = datetime.datetime.now(datetime.timezone.utc)
    deals = mt5.history_deals_get(now - datetime.timedelta(days=7), now) or []
    closed_rows = []
    for d in deals:
        if d.entry in (1, 2) and d.symbol:
            side = "BUY" if d.type == mt5.DEAL_TYPE_SELL else "SELL"
            closed_rows.append({
                "ticket": int(d.position_id or d.ticket),
                "symbol": d.symbol,
                "side": side,
                "volume": float(d.volume),
                "open_price": 0.0,
                "close_price": float(d.price),
                "profit": float(d.profit),
                "opened_at": datetime.datetime.fromtimestamp(d.time).isoformat(),
                "closed_at": datetime.datetime.fromtimestamp(d.time).isoformat(),
            })

    payload = {
        "status": {
            "is_running": is_running, "message": message,
            "account_equity": info.equity,
            "account_balance": info.balance,
            "account_currency": info.currency,
        },
        "positions": pos_rows,
        "pending_orders": pending_rows,
        "closed_trades": closed_rows,
    }
    res = _post(payload)
    if res:
        print(f"OK: bal={info.balance} pos={len(pos_rows)} pending={len(pending_rows)} history={len(closed_rows)}")


def log_ai_signal(symbol, signal, confidence, reasoning="", stop_loss_pips=None, take_profit_pips=None):
    _post({"ai_signal": {
        "symbol": symbol, "signal": signal, "confidence": confidence,
        "reasoning": reasoning,
        "stop_loss_pips": stop_loss_pips, "take_profit_pips": take_profit_pips,
    }})


def log_claude_cost(cost: float) -> None:
    if _post({"add_claude_cost": cost}):
        print(f"OK: Claude cost loglandi (${cost:.6f})")


# Backwards compat
def sync_bot_status(is_running=True, message="Bot is running"):
    sync_all(is_running, message)


def sync_positions():
    sync_all()


def sync_trade_history():
    sync_all()


def run_sync():
    sync_all()


if __name__ == "__main__":
    print("Loop: har 5 soniyada Cloud'ga yuborilyapti (Ctrl+C to'xtatish)")
    while True:
        try:
            sync_all()
        except Exception as e:
            print(f"loop error: {e}")
        time.sleep(5)
