"""
blackbox_exporter.py
====================
SQLite bazadagi 'ai_decisions' jadvalidan Qora Quti (Black Box)
statistikasini hisoblaydi va React UI ko'rishi uchun public/blackbox.json
fayliga eksport qiladi.
"""

import sqlite3
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

def export_blackbox_json(db_path: str = "decisions_log.db", output_path: str = "public/blackbox.json") -> None:
    """Black box ma'lumotlarini JSON faylga eksport qilish."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. Close Mechanism bo'yicha statistika
        cursor.execute('''
            SELECT
                COALESCE(close_mechanism, 'unknown') as mechanism,
                COUNT(*) as trade_count,
                SUM(CASE WHEN outcome_label = 'LOSS' THEN 1 ELSE 0 END) as loss_count,
                ROUND(SUM(outcome_profit), 2) as total_profit
            FROM ai_decisions
            WHERE outcome_label IS NOT NULL
            GROUP BY close_mechanism
            ORDER BY loss_count DESC
        ''')
        mechanism_stats = []
        for row in cursor.fetchall():
            mechanism_stats.append({
                "mechanism": str(row[0]),
                "trade_count": int(row[1]),
                "loss_count": int(row[2]),
                "total_profit": float(row[3] or 0.0)
            })

        # 2. News Coverage Gap bo'yicha statistika
        cursor.execute('''
            SELECT
                COALESCE(news_coverage_gap, 'NULL') as gap,
                COUNT(*) as trade_count,
                SUM(CASE WHEN outcome_label = 'LOSS' THEN 1 ELSE 0 END) as loss_count,
                ROUND(SUM(outcome_profit), 2) as total_profit
            FROM ai_decisions
            WHERE outcome_label IS NOT NULL
            GROUP BY news_coverage_gap
        ''')
        news_gap_stats = []
        for row in cursor.fetchall():
            news_gap_stats.append({
                "gap": str(row[0]),
                "trade_count": int(row[1]),
                "loss_count": int(row[2]),
                "total_profit": float(row[3] or 0.0)
            })

        # 3. News Strategy Style bo'yicha statistika
        cursor.execute('''
            SELECT
                COALESCE(news_strategy_type, 'NONE') as style,
                COUNT(*) as trade_count,
                SUM(CASE WHEN outcome_label = 'LOSS' THEN 1 ELSE 0 END) as loss_count,
                ROUND(SUM(outcome_profit), 2) as total_profit
            FROM ai_decisions
            WHERE outcome_label IS NOT NULL AND news_strategy_type IS NOT NULL
            GROUP BY news_strategy_type
        ''')
        news_style_stats = []
        for row in cursor.fetchall():
            news_style_stats.append({
                "style": str(row[0]),
                "trade_count": int(row[1]),
                "loss_count": int(row[2]),
                "total_profit": float(row[3] or 0.0)
            })

        # Yig'ma ma'lumot
        data = {
            "close_mechanism": mechanism_stats,
            "news_coverage_gap": news_gap_stats,
            "news_strategy_style": news_style_stats,
            "updated_at": datetime.now().isoformat()
        }

        # Fayl yozish
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        tmp_path = output_path + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, output_path)
            
        logger.info("Black box statistikasi eksport qilindi: %s", output_path)

    except sqlite3.OperationalError as e:
        logger.warning("Black box export xatosi (ustunlar yo'q bo'lishi mumkin): %s", e)
    except Exception as e:
        logger.error("Black box export kutilmagan xatolik: %s", e)
    finally:
        if 'conn' in locals():
            conn.close()
