"""
black_box_report.py
====================
Qora quti MVP hisoboti. decisions_log.db dagi ai_decisions jadvalidan
close_mechanism va news_coverage_gap bo'yicha zarar taqsimotini ko'rsatadi.

Ishlatish: python tools/black_box_report.py
"""

import sqlite3

DB_PATH = "decisions_log.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=== close_mechanism bo'yicha zarar taqsimoti ===")
    try:
        cursor.execute('''
            SELECT
                COALESCE(close_mechanism, 'NULL'),
                COUNT(*) as trade_count,
                SUM(CASE WHEN outcome_label = 'LOSS' THEN 1 ELSE 0 END) as loss_count,
                ROUND(SUM(outcome_profit), 2) as total_profit
            FROM ai_decisions
            WHERE outcome_label IS NOT NULL
            GROUP BY close_mechanism
            ORDER BY loss_count DESC
        ''')
        for row in cursor.fetchall():
            print(f"  {row[0]:30s} | savdolar: {row[1]:4d} | zararlar: {row[2]:4d} | jami P/L: {row[3]}")
    except sqlite3.OperationalError as e:
        print(f"Xatolik: {e}. 'close_mechanism' ustuni mavjud bo'lmasligi mumkin.")

    print("\n=== news_coverage_gap bo'yicha zarar taqsimoti ===")
    try:
        cursor.execute('''
            SELECT
                COALESCE(news_coverage_gap, 'NULL'),
                COUNT(*) as trade_count,
                SUM(CASE WHEN outcome_label = 'LOSS' THEN 1 ELSE 0 END) as loss_count
            FROM ai_decisions
            WHERE outcome_label IS NOT NULL
            GROUP BY news_coverage_gap
        ''')
        for row in cursor.fetchall():
            print(f"  gap={row[0]!s:10s} | savdolar: {row[1]:4d} | zararlar: {row[2]:4d}")
    except sqlite3.OperationalError as e:
        print(f"Xatolik: {e}. 'news_coverage_gap' ustuni mavjud bo'lmasligi mumkin.")

    conn.close()

if __name__ == "__main__":
    main()
