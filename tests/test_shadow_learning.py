import sys
import os
import sqlite3
import datetime
import unittest
from unittest.mock import MagicMock, patch

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from bot.engine.decision_logger import DecisionLogger
from bot.sync.supabase_sync import SupabaseSync

class TestShadowLearning(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_decisions.db"
        self.logger = DecisionLogger(db_path=self.db_path)
        
        # Insert a dummy pending order decision with ticket = 100
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ai_decisions") # clean table
        cursor.execute('''
            INSERT INTO ai_decisions 
            (timestamp, pair, timeframe, context_json, prompt, ai_response, final_decision, risk_pct, ticket)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.datetime.now().isoformat(),
            "EURUSD",
            "H1",
            "{}",
            "test_prompt",
            "test_response",
            "BUY_LIMIT",
            1.0,
            100  # PENDING ORDER TICKET
        ))
        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    @patch("bot.sync.supabase_sync.mt5")
    def test_pending_order_outcome(self, mock_mt5):
        # Mock MT5 Deal for DEAL_ENTRY_OUT (the closing deal)
        class MockDealOut:
            ticket = 401
            position_id = 200
            order = 400
            entry = 1
            type = 0
            symbol = "EURUSD"
            volume = 0.1
            price = 1.0500
            profit = 50.0  # WIN
            time = int(datetime.datetime.now().timestamp())
            
        # Mock MT5 Deal for DEAL_ENTRY_IN (the opening deal triggered by pending order)
        class MockDealIn:
            ticket = 301
            position_id = 200
            order = 100  # ORIGINAL PENDING ORDER TICKET!
            entry = 0
            type = 0
            symbol = "EURUSD"
            volume = 0.1
            price = 1.0450
            profit = 0.0
            time = int(datetime.datetime.now().timestamp())

        # When supabase_sync calls mt5.history_deals_get for the date range (closing deals)
        # and then for the specific position (to find original order)
        def mock_history_deals_get(*args, **kwargs):
            if "position" in kwargs:
                return [MockDealIn(), MockDealOut()]
            else:
                return [MockDealOut()]
                
        mock_mt5.history_deals_get.side_effect = mock_history_deals_get
        mock_mt5.DEAL_TYPE_BUY = 0
        config = MagicMock()
        sync = SupabaseSync(config=config)
        sync._post = MagicMock(return_value=True)  # Mock network call
        
        class MockInfo:
            equity = 1000
            balance = 1000
            currency = "USD"
            
        mock_mt5.account_info.return_value = MockInfo()
        mock_mt5.positions_get.return_value = []
        mock_mt5.orders_get.return_value = []
        
        # 1. Run sync_all which should return closed_trades
        closed_trades = sync.sync_all(mock_mt5, is_running=True, message="Test")
        
        self.assertEqual(len(closed_trades), 1)
        # Check if the extracted ticket is the original pending order ticket (100), not position_id (200)
        self.assertEqual(closed_trades[0]["ticket"], 100)
        
        # 2. Emulate main loop updating the outcome
        for ct in closed_trades:
            self.logger.update_outcome(ct["ticket"], ct["profit"])
            
        # 3. Verify in DB
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT outcome_label, outcome_profit FROM ai_decisions WHERE ticket = 100")
        row = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "WIN")
        self.assertEqual(row[1], 50.0)

if __name__ == "__main__":
    unittest.main()
