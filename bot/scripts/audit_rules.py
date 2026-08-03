import sqlite3
import csv
import argparse

def main():
    parser = argparse.ArgumentParser(description="AI Strategist qoidalarini audit qilish")
    parser.add_argument("--db", type=str, default="strategist_db.sqlite", help="SQLite bazasi yo'li")
    parser.add_argument("--export", type=str, help="Audit uchun CSV ga eksport qilish", default="rules_audit.csv")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()
    
    # Ma'lumotlar bazasi bor-yo'qligini tekshirish
    try:
        cursor.execute("SELECT count(*) FROM strategy_insights")
    except sqlite3.OperationalError:
        print("Ma'lumotlar bazasi hali yaratilmagan (yoki bo'sh).")
        return

    query = """
    SELECT 
        s.id, 
        k.title, 
        s.market_condition, 
        s.setup_type,
        s.insight_text, 
        s.success_count, 
        s.fail_count,
        (s.success_count + s.fail_count) as total_uses,
        CASE 
            WHEN (s.success_count + s.fail_count) > 0 
            THEN CAST(s.success_count AS FLOAT) / (s.success_count + s.fail_count) * 100 
            ELSE 0 
        END as win_rate,
        s.created_at,
        s.llm_model,
        s.chunk_index,
        s.source_chunk
    FROM strategy_insights s
    LEFT JOIN knowledge_sources k ON s.source_id = k.id
    ORDER BY total_uses DESC, win_rate DESC
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    print("="*60)
    print("📊 AI Strategist Qoidalari Auditi (Version Control & Traceability)")
    print("="*60)
    print(f"Umumiy qoidalar soni: {len(rows)}")
    
    with open(args.export, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "ID", "Kitob", "Bozor holati", "Setup", "Qoida", 
            "Foyda", "Zarar", "Umumiy", "WinRate %", 
            "Yaratilgan Sana", "LLM Modeli", "Chunk Index", "Manba Matni"
        ])
        for row in rows:
            writer.writerow(row)
            
    print(f"\n✅ To'liq ro'yxat '{args.export}' fayliga CSV formatida saqlandi.")
    print("Maslahat: CSV faylni Excel yoki Google Sheets'da ochib, qoidalarni mantiqan tekshiring.")
    print("Mantiqsiz qoidalarni o'chirish uchun ID bo'yicha quyidagi buyruqdan foydalanishingiz mumkin:")
    print("sqlite3 strategist_db.sqlite \"DELETE FROM strategy_insights WHERE id='...'\"")
    
    conn.close()

if __name__ == "__main__":
    main()
