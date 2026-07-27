"""
Supabase Cloud sync moduli.

Har sikl yakunida MT5 dan holat ma'lumotlarini oladi va
Cloud Edge Function ga POST qiladi.
"""
import logging
import datetime
from typing import Optional, Dict, Any, List

import requests
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)


class SupabaseSync:
    def __init__(self, config: Any):
        self.config = config
        self.endpoint = f"{config.supabase_url}/functions/v1/bot-sync" if config.supabase_url else None
        self.bot_sync_secret = config.bot_sync_secret
        self.mt5_login = str(config.mt5_login)
        self.last_sync_time = datetime.datetime(2000, 1, 1)
        self._last_reported_cost = 0.0

    def _post(self, payload: dict) -> Optional[dict]:
        """Supabase Edge Function ga POST yuboradi."""
        if not self.endpoint or not self.bot_sync_secret or not self.mt5_login:
            logger.warning("supabase_sync: SUPABASE_URL / BOT_SYNC_SECRET / MT5_LOGIN kerak")
            return None
        payload = {"mt5_login": self.mt5_login, **payload}
        try:
            r = requests.post(
                self.endpoint, json=payload,
                headers={"x-bot-secret": self.bot_sync_secret, "Content-Type": "application/json"},
                timeout=15,
            )
            if r.status_code >= 300:
                logger.error(f"bot-sync {r.status_code}: {r.text}")
                return None
            return r.json()
        except Exception as e:
            logger.error(f"bot-sync POST xatolik: {e}")
            return None

    def fetch_bot_settings(self) -> dict:
        """Cloud'dan bot sozlamalarini olish."""
        res = self._post({"ping": True})
        return (res or {}).get("settings") or {}

    @staticmethod
    def _order_type_name(t: int) -> str:
        return {
            mt5.ORDER_TYPE_BUY_LIMIT: "buy_limit",
            mt5.ORDER_TYPE_SELL_LIMIT: "sell_limit",
            mt5.ORDER_TYPE_BUY_STOP: "buy_stop",
            mt5.ORDER_TYPE_SELL_STOP: "sell_stop",
            mt5.ORDER_TYPE_BUY_STOP_LIMIT: "buy_stop_limit",
            mt5.ORDER_TYPE_SELL_STOP_LIMIT: "sell_stop_limit",
        }.get(t, "unknown")

    def sync_all(self, mt5_client: Any, is_running: bool = True, message: str = "Bot is running") -> None:
        """Bir POST bilan status + positions + pending_orders + history yuboradi."""
        info = mt5_client.get_account_info()
        if info is None:
            logger.error("Hisob ma'lumotlari yo'q — sync o'tkazib yuborildi")
            return

        # Positions
        positions = mt5_client.get_positions() or []
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
        orders = mt5_client.get_orders() or []
        pending_rows = []
        for o in orders:
            pending_rows.append({
                "ticket": int(o.ticket),
                "symbol": o.symbol,
                "type": self._order_type_name(o.type),
                "volume": float(o.volume_current),
                "price": float(o.price_open),
                "stop_loss": float(o.sl) if o.sl else None,
                "take_profit": float(o.tp) if o.tp else None,
            })

        # Closed history
        from_date = self.last_sync_time
        to_date = datetime.datetime.now() + datetime.timedelta(days=1)
        deals = mt5.history_deals_get(from_date, to_date) or []
        closed_rows = []
        for d in deals:
            if d.entry in (1, 2) and d.symbol:
                side = "BUY" if d.type == mt5.DEAL_TYPE_BUY else "SELL"
                
                # Original order ticket ni topish (Pending orderlar uchung)
                original_ticket = int(d.position_id or d.ticket)
                if d.position_id:
                    pos_deals = mt5.history_deals_get(position=d.position_id)
                    if pos_deals:
                        for pd in pos_deals:
                            if pd.entry == 0:  # DEAL_ENTRY_IN
                                original_ticket = int(pd.order)
                                break

                closed_rows.append({
                    "ticket": original_ticket,
                    "symbol": d.symbol,
                    "side": side,
                    "volume": float(d.volume),
                    "open_price": float(d.price) if hasattr(d, 'price') else 0.0,
                    "close_price": float(d.price),
                    "profit": float(d.profit),
                    "opened_at": datetime.datetime.fromtimestamp(d.time).isoformat(),
                    "closed_at": datetime.datetime.fromtimestamp(d.time).isoformat(),
                })
        self.last_sync_time = datetime.datetime.now()

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
        res = self._post(payload)
        if res:
            logger.info(f"Sync OK: bal={info.balance} pos={len(pos_rows)} pending={len(pending_rows)} history={len(closed_rows)}")
        
        return closed_rows

    def log_ai_signal(self, symbol: str, signal: str, confidence: int, reasoning: str = "",
                      entry_price: Optional[float] = None, sl_price: Optional[float] = None,
                      tp_price: Optional[float] = None, rr_ratio: Optional[float] = None,
                      stop_loss_pips: Optional[float] = None, take_profit_pips: Optional[float] = None) -> None:
        self._post({"ai_signal": {
            "symbol": symbol, "signal": signal, "confidence": confidence,
            "reasoning": reasoning,
            "entry_price": entry_price, "sl_price": sl_price,
            "tp_price": tp_price, "rr_ratio": rr_ratio,
            "stop_loss_pips": stop_loss_pips, "take_profit_pips": take_profit_pips,
        }})

    def log_claude_cost(self, total_cost: float) -> None:
        """Cumulative total_cost qabul qiladi va faqat delta ni Cloud'ga yuboradi."""
        delta = max(0.0, float(total_cost) - float(self._last_reported_cost))
        if delta <= 0:
            return
        if self._post({"add_claude_cost": delta}):
            self._last_reported_cost = float(total_cost)
            logger.info(f"Claude cost loglandi (+${delta:.6f}, jami ${total_cost:.6f})")
