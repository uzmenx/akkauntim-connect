import re

with open('bot/learning/ai_strategist.py', 'r') as f:
    code = f.read()

replacement = '''            if success:
                cursor.execute("UPDATE strategy_insights SET success_count = success_count + 1 WHERE id = ?", (insight_id,))
            else:
                cursor.execute("UPDATE strategy_insights SET fail_count = fail_count + 1 WHERE id = ?", (insight_id,))
            
            conn.commit()
            
            # Xato qoidalar filtri (Minus ball tizimi):
            # Agar qoida 5 marta ishlatilgan bo'lsa va 30% dan kam foyda keltirgan bo'lsa - o'chirish
            cursor.execute("SELECT success_count, fail_count FROM strategy_insights WHERE id = ?", (insight_id,))
            row = cursor.fetchone()
            if row:
                s_c, f_c = row
                tot = s_c + f_c
                if tot >= 5 and (s_c / tot) < 0.30:
                    # Qoidani o'chirish
                    cursor.execute("DELETE FROM strategy_insights WHERE id = ?", (insight_id,))
                    try:
                        self.collection.delete(ids=[insight_id])
                        import logging
                        logging.getLogger(__name__).warning(f"❌ Qoida {insight_id} o'chirildi (WinRate: {s_c/tot*100:.0f}%, {s_c} ta foyda, {f_c} ta zarar)")
                    except Exception:
                        pass
                    conn.commit()
                    if hasattr(self, 'sync_client') and self.sync_client:
                        # Optional: Supabase'dan ham o'chirish yoki active=false qilish mumkin
                        pass
                else:
                    # Yangi qiymatlarni o'qib olib Supabase'ga jo'natish
                    if hasattr(self, 'sync_client') and self.sync_client:
                        self.sync_client.update_insight(insight_id, {
                            "success_count": s_c,
                            "fail_count": f_c
                        })'''

code = code.replace('''            if success:
                cursor.execute("UPDATE strategy_insights SET success_count = success_count + 1 WHERE id = ?", (insight_id,))
            else:
                cursor.execute("UPDATE strategy_insights SET fail_count = fail_count + 1 WHERE id = ?", (insight_id,))
            
            conn.commit()
            
            # Yangi qiymatlarni o'qib olib Supabase'ga jo'natish
            if hasattr(self, 'sync_client') and self.sync_client:
                cursor.execute("SELECT success_count, fail_count FROM strategy_insights WHERE id = ?", (insight_id,))
                row = cursor.fetchone()
                if row:
                    self.sync_client.update_insight(insight_id, {
                        "success_count": row[0],
                        "fail_count": row[1]
                    })''', replacement)

with open('bot/learning/ai_strategist.py', 'w') as f:
    f.write(code)

