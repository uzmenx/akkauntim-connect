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
import sqlite3
import json
import os

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

    def _get_decision_metadata(self, ticket: int) -> tuple[List[str], bool]:
        """Local bazadan ticket bo'yicha strategiyalar va AI ishlatilganligini topadi."""
        db_path = 'decisions_log.db'
        if not os.path.exists(db_path):
            return [], False
        try:
            conn = sqlite3.connect(db_path, timeout=5)
            cur = conn.cursor()
            cur.execute("SELECT context_json, ai_response FROM ai_decisions WHERE ticket = ? ORDER BY id DESC LIMIT 1", (ticket,))
            row = cur.fetchone()
            conn.close()
            if not row:
                return [], False
            
            ctx = json.loads(row[0]) if row[0] else {}
            ai_resp_str = row[1]
            ai_resp = {}
            if ai_resp_str:
                try:
                    ai_resp = json.loads(ai_resp_str)
                except Exception:
                    pass
            
            ai_used = False
            if isinstance(ai_resp, dict) and ai_resp.get("signal") in ["BUY", "SELL"]:
                ai_used = True
            
            agreed = []
            if isinstance(ctx, dict) and "voting_result" in ctx:
                agreed = ctx["voting_result"].get("agreed_strategies", [])
                
            return agreed, ai_used
        except Exception as e:
            logger.debug(f"Failed to read decision metadata for {ticket}: {e}")
            return [], False

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

                agreed_strategies, ai_used = self._get_decision_metadata(original_ticket)

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
                    "mt5_comment": str(d.comment) if getattr(d, 'comment', None) else "",
                    "mt5_reason": int(d.reason) if hasattr(d, 'reason') else None,
                    "agreed_strategies": agreed_strategies,
                    "ai_used": ai_used
                })
        self.last_sync_time = datetime.datetime.now()

        # get available symbols
        available_symbols = {}
        if hasattr(mt5_client, "get_grouped_symbols"):
            available_symbols = mt5_client.get_grouped_symbols()

        payload = {
            "status": {
                "is_running": is_running, "message": message,
                "account_equity": info.equity,
                "account_balance": info.balance,
                "account_currency": info.currency,
                "available_symbols": available_symbols,
            },
            "positions": pos_rows,
            "pending_orders": pending_rows,
            "closed_trades": closed_rows,
        }
        res = self._post(payload)
        if res:
            logger.info(f"Sync OK: bal={info.balance} pos={len(pos_rows)} pending={len(pending_rows)} history={len(closed_rows)}")
        
        return closed_rows

    def sync_chart_data(self, symbol: str, timeframe: str, candles: List[dict], smc_zones: List[dict]) -> None:
        """SMC va Candles ma'lumotlarini UI uchun yuboradi"""
        payload = {
            "candles": candles,
            "smc_zones": smc_zones
        }
        res = self._post(payload)
        if res:
            logger.info(f"Chart data sync OK: {symbol} {timeframe} - {len(candles)} candles, {len(smc_zones)} zones")

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

    def log_regime(self, symbol: str, timeframe: str, regime: str, adx_value: float, vol_pct: float) -> None:
        self._post({"regime": {
            "symbol": symbol,
            "timeframe": timeframe,
            "regime": regime,
            "adx_value": adx_value,
            "volatility_pct": vol_pct
        }})

    def log_strategy_performance(self, strategy_name: str, regime: str, win_rate: float, trades_count: int) -> None:
        self._post({"strategy_performance": {
            "strategy_name": strategy_name,
            "regime": regime,
            "win_rate": win_rate,
            "trades_count": trades_count
        }})

    def log_claude_cost(self, total_cost: float) -> None:
        """Cumulative total_cost qabul qiladi va faqat delta ni Cloud'ga yuboradi."""
        delta = max(0.0, float(total_cost) - float(self._last_reported_cost))
        if delta <= 0:
            return
        if self._post({"add_claude_cost": delta}):
            self._last_reported_cost = float(total_cost)
            logger.info(f"Claude cost loglandi (+${delta:.6f}, jami ${total_cost:.6f})")

    def check_pending_books(self) -> List[dict]:
        """Supabase'dan o'qilishi kerak bo'lgan kitoblarni oladi."""
        if not self.config.supabase_url or not self.config.supabase_key:
            return []
        url = f"{self.config.supabase_url}/rest/v1/pending_books?status=eq.pending"
        headers = {
            "apikey": self.config.supabase_key,
            "Authorization": f"Bearer {self.config.supabase_key}"
        }
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.error(f"check_pending_books xatolik: {e}")
        return []

    def update_book_status(self, book_id: str, status: str) -> None:
        """Kitob statusini yangilaydi (processing, done, error)."""
        if not self.config.supabase_url or not self.config.supabase_key:
            return
        url = f"{self.config.supabase_url}/rest/v1/pending_books?id=eq.{book_id}"
        headers = {
            "apikey": self.config.supabase_key,
            "Authorization": f"Bearer {self.config.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        try:
            requests.patch(url, headers=headers, json={"status": status}, timeout=10)
        except Exception as e:
            logger.error(f"update_book_status xatolik: {e}")

    def upload_insight(self, insight: dict) -> None:
        """AIStrategist qoidasini Supabase'ga yuboradi."""
        if not self.config.supabase_url or not self.config.supabase_key:
            return
        url = f"{self.config.supabase_url}/rest/v1/strategy_insights"
        headers = {
            "apikey": self.config.supabase_key,
            "Authorization": f"Bearer {self.config.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        try:
            requests.post(url, headers=headers, json=insight, timeout=10)
        except Exception as e:
            logger.error(f"upload_insight xatolik: {e}")

    def update_insight(self, insight_id: str, updates: dict) -> None:
        """Supabase'dagi insight'ni yangilaydi (masalan: success_count)."""
        if not self.config.supabase_url or not self.config.supabase_key:
            return
        url = f"{self.config.supabase_url}/rest/v1/strategy_insights?id=eq.{insight_id}"
        headers = {
            "apikey": self.config.supabase_key,
            "Authorization": f"Bearer {self.config.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        try:
            requests.patch(url, headers=headers, json=updates, timeout=10)
        except Exception as e:
            logger.error(f"update_insight xatolik: {e}")

    def upload_memory(self, memory_data: dict) -> None:
        """AI saboqni Supabase'ga yuboradi."""
        if not self.config.supabase_url or not self.config.supabase_key:
            return
        url = f"{self.config.supabase_url}/rest/v1/ai_memory"
        headers = {
            "apikey": self.config.supabase_key,
            "Authorization": f"Bearer {self.config.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        try:
            requests.post(url, headers=headers, json=memory_data, timeout=10)
        except Exception as e:
            logger.error(f"upload_memory xatolik: {e}")

    def update_memory(self, lesson_id: str, updates: dict) -> None:
        """Supabase'dagi saboqni (ai_memory) yangilaydi (masalan: success_applications)."""
        if not self.config.supabase_url or not self.config.supabase_key:
            return
        url = f"{self.config.supabase_url}/rest/v1/ai_memory?id=eq.{lesson_id}"
        headers = {
            "apikey": self.config.supabase_key,
            "Authorization": f"Bearer {self.config.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        try:
            requests.patch(url, headers=headers, json=updates, timeout=10)
        except Exception as e:
            logger.error(f"update_memory xatolik: {e}")

    def upload_strategy_performance(self, perf_data: dict) -> None:
        """Strategiya samaradorligini Supabase'ga yuboradi."""
        if not self.config.supabase_url or not self.config.supabase_key:
            return
        url = f"{self.config.supabase_url}/rest/v1/strategy_performance"
        headers = {
            "apikey": self.config.supabase_key,
            "Authorization": f"Bearer {self.config.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        try:
            requests.post(url, headers=headers, json=perf_data, timeout=10)
        except Exception as e:
            logger.error(f"upload_strategy_performance xatolik: {e}")
