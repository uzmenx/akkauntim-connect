"""
ai_memory.py — AI Doimiy Xotira Tizimi.

AI ning har bir savdo va kitobdan o'rgangan saboqlarini
doimiy saqlaydi. Har safar savdo qarorida eng muhim
saboqlarni promptga qo'shib beradi.

Kategoriyalar:
- trade_pattern: Savdo naqshlaridan olingan saboqlar
- risk_management: Risk boshqarish bo'yicha saboqlar  
- market_regime: Bozor rejimi kuzatuvlari
- strategy_effectiveness: Strategiya samaradorligi haqida
- book_knowledge: Kitoblardan olingan umumiy bilimlar
"""

import json
import sqlite3
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid

logger = logging.getLogger(__name__)


class AIMemory:
    """AI ning doimiy xotirasi — saboqlar, kuzatuvlar, va xulosalarni saqlaydi."""
    
    def __init__(self, db_path: str = 'ai_memory.db'):
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if not os.path.isabs(db_path):
            self.db_path = os.path.join(root_dir, db_path)
        else:
            self.db_path = db_path
            
        self.sync_client = None  # SupabaseSync instance (cloud backup uchun)
        self._init_db()
    
    def _init_db(self):
        """SQLite jadvallarini yaratish."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_lessons (
                    id TEXT PRIMARY KEY,
                    lesson_text TEXT NOT NULL,
                    category TEXT NOT NULL,
                    importance INTEGER DEFAULT 5,
                    source TEXT DEFAULT 'trade_review',
                    success_applications INTEGER DEFAULT 0,
                    failed_applications INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    active INTEGER DEFAULT 1
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT NOT NULL,
                    period TEXT NOT NULL,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    total_profit REAL DEFAULT 0.0,
                    avg_rr REAL DEFAULT 0.0,
                    recommended_weight REAL DEFAULT 1.0,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    observation TEXT NOT NULL,
                    regime TEXT,
                    symbols TEXT,
                    created_at TEXT NOT NULL
                )
            ''')
            
            conn.commit()
        except Exception as e:
            logger.error(f"AI Memory DB init xatolik: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
    
    def add_lesson(self, lesson_text: str, category: str, 
                   importance: int = 5, source: str = 'trade_review') -> str:
        """
        Yangi saboqni xotiraga qo'shish.
        
        Args:
            lesson_text: Saboq matni
            category: trade_pattern, risk_management, market_regime, strategy_effectiveness, book_knowledge
            importance: 1-10 (10 = eng muhim)
            source: trade_review, book, manual
        Returns:
            lesson_id
        """
        lesson_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Dublikat tekshiruvi — o'xshash saboq allaqachon bormi?
            cursor.execute(
                "SELECT id, importance FROM ai_lessons WHERE lesson_text = ? AND active = 1",
                (lesson_text,)
            )
            existing = cursor.fetchone()
            if existing:
                # Mavjud saboqning muhimligini oshirish
                new_importance = min(10, existing[1] + 1)
                cursor.execute(
                    "UPDATE ai_lessons SET importance = ?, updated_at = ? WHERE id = ?",
                    (new_importance, now, existing[0])
                )
                conn.commit()
                conn.close()
                logger.info(f"Mavjud saboq kuchaytirildi (importance: {new_importance})")
                return existing[0]
            
            cursor.execute('''
                INSERT INTO ai_lessons (id, lesson_text, category, importance, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (lesson_id, lesson_text, category, importance, source, now, now))
            
            conn.commit()
            logger.info(f"Yangi saboq saqlandi: [{category}] {lesson_text[:60]}...")
            
            # Cloud ga yuborish
            self._sync_lesson_to_cloud(lesson_id, lesson_text, category, importance, source, now)
            
        except Exception as e:
            logger.error(f"Saboq saqlashda xatolik: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
        
        return lesson_id
    
    def get_recent_lessons(self, limit: int = 7, category: Optional[str] = None) -> str:
        """
        Eng muhim va yangi saboqlarni formatlangan matn ko'rinishida qaytarish.
        Promptga qo'shish uchun tayyor.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if category:
                cursor.execute('''
                    SELECT lesson_text, category, importance, success_applications, failed_applications
                    FROM ai_lessons 
                    WHERE active = 1 AND category = ?
                    ORDER BY importance DESC, updated_at DESC 
                    LIMIT ?
                ''', (category, limit))
            else:
                cursor.execute('''
                    SELECT lesson_text, category, importance, success_applications, failed_applications
                    FROM ai_lessons 
                    WHERE active = 1
                    ORDER BY importance DESC, updated_at DESC 
                    LIMIT ?
                ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return "AI xotirasi hali bo'sh. Savdolar va kitoblardan saboqlar to'planishi kerak."
            
            lines = []
            for i, (text, cat, imp, success, fail) in enumerate(rows, 1):
                total = success + fail
                effectiveness = ""
                if total > 0:
                    rate = success / total * 100
                    effectiveness = f" [Qo'llanildi: {total} marta, {rate:.0f}% samarali]"
                
                emoji = {"trade_pattern": "📊", "risk_management": "🛡️", 
                         "market_regime": "🌊", "strategy_effectiveness": "⚡",
                         "book_knowledge": "📚"}.get(cat, "💡")
                
                lines.append(f"{i}. {emoji} [{cat}] (muhimlik: {imp}/10) {text}{effectiveness}")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Saboqlarni olishda xatolik: {e}")
            return ""
    
    def record_lesson_application(self, lesson_id: str, success: bool):
        """Saboqning qo'llanilganini qayd qilish (samaradorlikni kuzatish)."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if success:
                cursor.execute(
                    "UPDATE ai_lessons SET success_applications = success_applications + 1, updated_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), lesson_id)
                )
            else:
                cursor.execute(
                    "UPDATE ai_lessons SET failed_applications = failed_applications + 1, updated_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), lesson_id)
                )
                
                # Agar ko'p marta ishlamasa — muhimligini kamaytirish
                cursor.execute("SELECT failed_applications, importance FROM ai_lessons WHERE id = ?", (lesson_id,))
                row = cursor.fetchone()
                if row and row[0] >= 5 and row[1] > 1:
                    cursor.execute(
                        "UPDATE ai_lessons SET importance = importance - 1 WHERE id = ?",
                        (lesson_id,)
                    )
            
            conn.commit()
            
            # Yangi qiymatlarni o'qib olib Supabase'ga jo'natish
            if hasattr(self, 'sync_client') and self.sync_client:
                cursor.execute("SELECT success_applications, failed_applications, importance FROM ai_lessons WHERE id = ?", (lesson_id,))
                row = cursor.fetchone()
                if row:
                    self.sync_client.update_memory(lesson_id, {
                        "success_applications": row[0],
                        "failed_applications": row[1],
                        "importance": row[2]
                    })
        except Exception as e:
            logger.error(f"Lesson application qayd qilishda xatolik: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
    
    def save_strategy_performance(self, strategy_name: str, wins: int, losses: int, 
                                   total_profit: float, avg_rr: float, 
                                   recommended_weight: float):
        """Strategiya samaradorligini saqlash."""
        now = datetime.now()
        period = now.strftime("%Y-%m-%d")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Bugungi yozuv bormi?
            cursor.execute(
                "SELECT id FROM strategy_performance WHERE strategy_name = ? AND period = ?",
                (strategy_name, period)
            )
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute('''
                    UPDATE strategy_performance 
                    SET wins = ?, losses = ?, total_profit = ?, avg_rr = ?, 
                        recommended_weight = ?, updated_at = ?
                    WHERE id = ?
                ''', (wins, losses, total_profit, avg_rr, recommended_weight, now.isoformat(), existing[0]))
            else:
                cursor.execute('''
                    INSERT INTO strategy_performance 
                    (strategy_name, period, wins, losses, total_profit, avg_rr, recommended_weight, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (strategy_name, period, wins, losses, total_profit, avg_rr, recommended_weight, now.isoformat()))
            
            conn.commit()
            
            # Cloud ga yuborish
            self._sync_strategy_perf_to_cloud(strategy_name, wins, losses, total_profit, avg_rr, recommended_weight)
            
        except Exception as e:
            logger.error(f"Strategy performance saqlashda xatolik: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
    
    def get_strategy_weights(self) -> Dict[str, float]:
        """Eng so'nggi strategiya vaznlarini qaytarish."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT strategy_name, recommended_weight 
                FROM strategy_performance 
                WHERE id IN (
                    SELECT MAX(id) FROM strategy_performance GROUP BY strategy_name
                )
            ''')
            
            weights = {}
            for row in cursor.fetchall():
                weights[row[0]] = row[1]
            
            conn.close()
            return weights
            
        except Exception as e:
            logger.error(f"Strategy weights olishda xatolik: {e}")
            return {}
    
    def auto_extract_lessons(self, review_summary: str, llm_call_fn) -> List[str]:
        """
        AI Review natijasidan avtomatik saboqlar chiqarish.
        
        Args:
            review_summary: AI Review ning analysis_summary matni
            llm_call_fn: LLM ga so'rov yuborish funksiyasi
        Returns:
            Saqlangan saboqlar ID lari
        """
        prompt = f"""Sen trading AI ning xotira modulisan.
Quyidagi savdo tahlili natijasidan 2-4 ta qisqa, aniq, amaliy saboq chiqar.
Har bir saboq kelajakda qaror qilishda foydali bo'lishi kerak.

Tahlil natijasi:
{review_summary}

Faqat JSON formatida javob ber (boshqa matn yozma):
{{
  "lessons": [
    {{
      "text": "Saboq matni (1-2 gap, aniq va amaliy)",
      "category": "trade_pattern" yoki "risk_management" yoki "market_regime" yoki "strategy_effectiveness",
      "importance": 5  // 1-10
    }}
  ]
}}"""
        
        try:
            response_text = llm_call_fn(prompt)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response_text[json_start:json_end])
            else:
                return []
            
            saved_ids = []
            for lesson in data.get("lessons", []):
                lesson_id = self.add_lesson(
                    lesson_text=lesson.get("text", ""),
                    category=lesson.get("category", "trade_pattern"),
                    importance=lesson.get("importance", 5),
                    source="trade_review"
                )
                saved_ids.append(lesson_id)
            
            logger.info(f"AI xotirasiga {len(saved_ids)} ta yangi saboq saqlandi")
            return saved_ids
            
        except Exception as e:
            logger.error(f"Auto extract lessons xatolik: {e}")
            return []
    
    def add_observation(self, observation: str, regime: str = "", symbols: str = ""):
        """Bozor kuzatuvini saqlash."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO market_observations (observation, regime, symbols, created_at)
                VALUES (?, ?, ?, ?)
            ''', (observation, regime, symbols, datetime.now().isoformat()))
            conn.commit()
        except Exception as e:
            logger.error(f"Observation saqlashda xatolik: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Xotira statistikasini olish."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM ai_lessons WHERE active = 1")
            total_lessons = cursor.fetchone()[0]
            
            cursor.execute("SELECT category, COUNT(*) FROM ai_lessons WHERE active = 1 GROUP BY category")
            by_category = dict(cursor.fetchall())
            
            cursor.execute("SELECT COUNT(DISTINCT strategy_name) FROM strategy_performance")
            tracked_strategies = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM market_observations")
            total_observations = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "total_lessons": total_lessons,
                "lessons_by_category": by_category,
                "tracked_strategies": tracked_strategies,
                "total_observations": total_observations
            }
        except Exception as e:
            logger.error(f"Memory statistics xatolik: {e}")
            return {}
    
    # ==================== CLOUD SYNC ====================
    
    def _sync_lesson_to_cloud(self, lesson_id: str, text: str, category: str, 
                               importance: int, source: str, created_at: str):
        """Saboqni Supabase ga yuborish."""
        if not self.sync_client:
            return
        try:
            self.sync_client.upload_memory({
                "id": lesson_id,
                "lesson_text": text,
                "category": category,
                "importance": importance,
                "source": source,
                "created_at": created_at
            })
        except Exception as e:
            logger.warning(f"Cloud ga saboq yuborishda xatolik: {e}")
    
    def _sync_strategy_perf_to_cloud(self, strategy_name: str, wins: int, losses: int,
                                      total_profit: float, avg_rr: float, weight: float):
        """Strategiya samaradorligini Supabase ga yuborish."""
        if not self.sync_client:
            return
        try:
            self.sync_client.upload_strategy_performance({
                "strategy_name": strategy_name,
                "wins": wins,
                "losses": losses, 
                "total_profit": total_profit,
                "avg_rr": avg_rr,
                "recommended_weight": weight
            })
        except Exception as e:
            logger.warning(f"Cloud ga strategiya samaradorligi yuborishda xatolik: {e}")
