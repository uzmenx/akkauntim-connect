"""
Unit test for JSON optimizations (news_cache.json and blackbox.json)
"""

import sys
from unittest.mock import MagicMock

# Mock dependencies if not installed in test environment
for mod in ['requests', 'pandas', 'dateutil', 'dateutil.parser']:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

import os
import json
import tempfile
import sqlite3
from unittest.mock import patch
from bot.strategy.news.detector import NewsDetector
from bot.engine.blackbox_exporter import export_blackbox_json

def test_news_cache_optimization():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = os.path.join(tmpdir, "news_cache.json")
        detector = NewsDetector()
        detector.cache_file = cache_path
        
        test_data = [{"id": 1, "title": "Test Event", "country": "USD"}]
        
        # Mock requests.get
        with patch("bot.strategy.news.detector.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = test_data
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp
            
            # 1-call: Network request triggered, file written
            res1 = detector.fetch_calendar(force_refresh=True)
            assert res1 is True
            assert mock_get.call_count == 1
            assert os.path.exists(cache_path)
            
            # 2-call: In-memory cache hit (no network, no disk re-read)
            res2 = detector.fetch_calendar(force_refresh=False)
            assert res2 is True
            assert mock_get.call_count == 1  # count didn't increase!
            
            print("✅ news_cache.json in-memory & atomic caching test PASSED!")

def test_blackbox_json_deduplication():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "decisions_log.db")
        json_path = os.path.join(tmpdir, "blackbox.json")
        
        # Create DB
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_decisions (
                id INTEGER PRIMARY KEY,
                close_mechanism TEXT,
                news_coverage_gap TEXT,
                news_strategy_type TEXT,
                outcome_label TEXT,
                outcome_profit REAL
            )
        """)
        conn.execute("INSERT INTO ai_decisions VALUES (1, 'TP', '0-10m', 'STRADDLE', 'WIN', 100.0)")
        conn.commit()
        conn.close()
        
        # 1st Export: file created
        export_blackbox_json(db_path=db_path, output_path=json_path, force=True)
        assert os.path.exists(json_path)
        mtime1 = os.path.getmtime(json_path)
        
        # 2nd Export without changes: file NOT overwritten (mtime remains same)
        export_blackbox_json(db_path=db_path, output_path=json_path, force=False)
        mtime2 = os.path.getmtime(json_path)
        assert mtime1 == mtime2
        
        print("✅ blackbox.json deduplication test PASSED!")

if __name__ == "__main__":
    test_news_cache_optimization()
    test_blackbox_json_deduplication()
