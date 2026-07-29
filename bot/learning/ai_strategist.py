"""
ai_strategist.py

MUHIM ARXITEKTURA QARORI (YANGILANGAN - SHADOW LEARNING v2):

BOSQICH A — OFFLINE (kitob qo'shilganda):
  - Kitob o'qiladi (yangi Async/Chunking orqali tezlashishi mumkin).
  - LLM dan aniq JSON formatida qoidalar (insights) olinadi.
  - Ma'lumotlar ham SQLite'ga, ham RAG uchun ChromaDB vektor bazasiga saqlanadi.

BOSQICH B — ONLINE (trade signalida):
  - Bozorning joriy holati tekst ko'rinishida beriladi (masalan: "EURUSD, H1, SMC bullish OB").
  - ChromaDB joriy holatga eng mos 3 ta (semantik o'xshash) strategiya qoidasini topib beradi.
  - Bu qoidalar ularning o'tmishdagi Win Rate (muvaffaqiyat darajasi) bilan birga qaytariladi.
  - LLM (Claude) shu ma'lumotlar asosida yakuniy qaror chiqaradi.

BOSQICH C — FEEDBACK (trade yopilgandan so'ng):
  - `record_trade_result` chaqiriladi.
  - AI qabul qilgan qaror foyda (Win) yoki zarar (Loss) keltirganiga qarab, 
    bazadagi strategiya qoidasining `success_count` yoki `fail_count` qiymati yangilanadi.
  - Bu haqiqiy "Shadow Learning" ni ta'minlaydi!
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import hashlib
import uuid

import chromadb
from chromadb.config import Settings

from bot.learning.file_reader import extract_text


class AIStrategist:
    def __init__(
        self,
        llm_call_fn,
        knowledge_base_dir: str = "knowledge_base",
        db_path: str = "strategist_db.sqlite",
        chroma_db_dir: str = "chroma_db",
    ):
        self.llm_call = llm_call_fn
        self.knowledge_base_dir = Path(knowledge_base_dir)
        self.knowledge_base_dir.mkdir(exist_ok=True)
        
        self.db_path = db_path
        self.chroma_db_dir = chroma_db_dir
        
        self._init_sqlite()
        self._init_chroma()

    def _init_sqlite(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                author TEXT,
                language TEXT,
                file_path TEXT,
                content_hash TEXT UNIQUE,
                category TEXT,
                added_date TEXT,
                processed INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_insights (
                id TEXT PRIMARY KEY, 
                source_id INTEGER,
                insight_text TEXT,
                market_condition TEXT,
                setup_type TEXT,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                FOREIGN KEY (source_id) REFERENCES knowledge_sources(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insight_id TEXT,
                success INTEGER,
                pnl REAL,
                reason TEXT,
                timestamp TEXT,
                FOREIGN KEY (insight_id) REFERENCES strategy_insights(id)
            )
        """)

        conn.commit()
        conn.close()

    def _init_chroma(self):
        # Persistent ChromaDB klientini ishga tushirish
        self.chroma_client = chromadb.PersistentClient(path=self.chroma_db_dir)
        self.collection = self.chroma_client.get_or_create_collection(
            name="trading_insights",
            metadata={"hnsw:space": "cosine"} # O'xshashlikni o'lchash usuli
        )

    # ==================== BOSQICH A: OFFLINE ====================

    def add_knowledge_source(
        self,
        file_path: str,
        title: str,
        author: str = "",
        language: str = "en",
        category: str = "book",
    ):
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"❌ Fayl topilmadi: {file_path}")
            return False

        content = extract_text(file_path)
        if content is None:
            return False

        content_hash = hashlib.md5(content.encode()).hexdigest()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO knowledge_sources
                (title, author, language, file_path, content_hash, category, added_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (title, author, language, str(file_path), content_hash, category, datetime.now().isoformat()),
            )
            source_id = cursor.lastrowid
            conn.commit()
        except sqlite3.IntegrityError:
            print(f"⚠️ '{title}' allaqachon mavjud (bir xil kontent)")
            conn.close()
            return False

        conn.close()

        print(f"✅ Qo'shildi: '{title}' ({language}), {len(content)} belgi")
        print("🔄 Tahlil qilinmoqda (bu bir necha daqiqa davom etishi mumkin)...")
        return self._process_source(source_id, content)

    def _process_source(self, source_id: int, content: str):
        chunks = self._chunk_text(content, max_chars=4000)
        insights_saved = 0

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for i, chunk in enumerate(chunks):
            prompt = f"""Siz professional trading strategiyasi tahlilchisisiz.
Quyidagi matnni tahlil qiling va unda qandaydir trading strategiyasi (entry/exit/risk) bormi shuni aniqlang.

Matn qismi {i+1}/{len(chunks)}:
{chunk}

Faqat va faqat JSON formatida javob qaytaring (boshqa gap qo'shmang):
{{
  "has_strategy": true yoki false,
  "market_condition": "trend" yoki "range" yoki "volatile" yoki "all",
  "setup_type": "Qisqacha qanday setup ekani (masalan, 'breakout', 'order_block')",
  "insight": "Strategiya qoidasining 2-3 gaplik aniq ta'rifi"
}}
Agar matnda aniq strategiya yo'q bo'lsa, "has_strategy": false qaytaring.
"""
            response_text = self.llm_call(prompt)
            
            try:
                # LLM javobi ichidan JSON ni qirqib olish
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    data = json.loads(json_str)
                else:
                    data = {"has_strategy": False}
            except Exception as e:
                print(f"JSON parsing error: {e}")
                data = {"has_strategy": False}

            if not data.get("has_strategy"):
                continue

            insight_id = str(uuid.uuid4())
            insight_text = data.get("insight", "")
            condition = data.get("market_condition", "all").lower()
            setup_type = data.get("setup_type", "unknown")

            # 1. SQLite'ga saqlash
            cursor.execute(
                """
                INSERT INTO strategy_insights (id, source_id, insight_text, market_condition, setup_type)
                VALUES (?, ?, ?, ?, ?)
                """,
                (insight_id, source_id, insight_text, condition, setup_type),
            )
            
            # 2. ChromaDB'ga saqlash (Vektor qidiruv uchun)
            self.collection.add(
                documents=[insight_text],
                metadatas=[{
                    "source_id": source_id, 
                    "market_condition": condition,
                    "setup_type": setup_type
                }],
                ids=[insight_id]
            )
            
            # 3. Supabase'ga yuborish (Dashboard uchun)
            if hasattr(self, 'sync_client') and self.sync_client:
                try:
                    self.sync_client.upload_insight({
                        "id": insight_id,
                        "insight_text": insight_text,
                        "market_condition": condition,
                        "setup_type": setup_type
                    })
                except Exception as e:
                    print(f"Supabase'ga yuborishda xatolik: {e}")
            
            insights_saved += 1

        cursor.execute("UPDATE knowledge_sources SET processed = 1 WHERE id = ?", (source_id,))
        conn.commit()
        conn.close()

        print(f"✅ {insights_saved} ta xulosa saqlandi ({len(chunks)} qismdan)")
        return (True, insights_saved, len(chunks))

    def _chunk_text(self, text: str, max_chars: int = 4000) -> List[str]:
        chunks = []
        current = ""
        for paragraph in text.split("\n\n"):
            if len(current) + len(paragraph) < max_chars:
                current += paragraph + "\n\n"
            else:
                if current:
                    chunks.append(current.strip())
                current = paragraph + "\n\n"
        if current:
            chunks.append(current.strip())
        return chunks

    # ==================== BOSQICH B: ONLINE (RAG) ====================

    def get_relevant_context(self, current_situation_desc: str, market_condition: str, limit: int = 3) -> str:
        """
        Bozordagi hozirgi holatni ta'riflovchi matnni olib, shunga eng mos kitob qoidalarini topadi.
        ChromaDB orqali ishlaydi (Semantic Search).
        """
        try:
            results = self.collection.query(
                query_texts=[current_situation_desc],
                n_results=limit,
                where={"$or": [{"market_condition": market_condition}, {"market_condition": "all"}]}
            )
        except Exception:
            return ""

        if not results['documents'] or not results['documents'][0]:
            return ""
            
        found_ids = results['ids'][0]
        found_docs = results['documents'][0]
        
        # SQLite dan ularning Win/Loss statistikasini olib kelamiz
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        formatted_insights = []
        for i in range(len(found_ids)):
            insight_id = found_ids[i]
            insight_text = found_docs[i]
            
            cursor.execute("SELECT success_count, fail_count FROM strategy_insights WHERE id=?", (insight_id,))
            row = cursor.fetchone()
            if row:
                success_count, fail_count = row
                total = success_count + fail_count
                win_rate = (success_count / total * 100) if total > 0 else 0
                
                feedback_str = f"[Statistika: {success_count} marta foyda, {fail_count} marta zarar qildi (WinRate: {win_rate:.0f}%)]"
            else:
                feedback_str = "[Yangi qoida, hali sinalmagan]"
                
            formatted_insights.append(f"- (ID: {insight_id}) {insight_text} {feedback_str}")
            
        conn.close()

        return "\n\n".join(formatted_insights)

    # ==================== BOSQICH C: FEEDBACK LOOP ====================
    
    def record_trade_result(self, insight_id: str, success: bool, pnl: float, reason: str = ""):
        """
        Trade tugagandan so'ng natijani tizimga qaytarish.
        Bu AI ning xatosidan o'rganishini (Shadow Learning) ta'minlaydi.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO trade_feedback (insight_id, success, pnl, reason, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (insight_id, int(success), pnl, reason, datetime.now().isoformat())
            )
            
            if success:
                cursor.execute("UPDATE strategy_insights SET success_count = success_count + 1 WHERE id = ?", (insight_id,))
            else:
                cursor.execute("UPDATE strategy_insights SET fail_count = fail_count + 1 WHERE id = ?", (insight_id,))
                
            conn.commit()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Trade result yozishda xatolik: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
        
        result_text = "Foyda" if success else "Zarar"
        print(f"🔄 Feedback qabul qilindi: Insight {insight_id[:6]}... -> {result_text}")

    def get_statistics(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM knowledge_sources WHERE processed = 1")
        total_books = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM strategy_insights")
        total_insights = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM trade_feedback")
        total_trades = cursor.fetchone()[0]

        conn.close()

        try:
            vector_count = self.collection.count()
        except:
            vector_count = 0

        return {
            "total_books": total_books,
            "total_insights_sqlite": total_insights,
            "total_insights_vector": vector_count,
            "total_trades_analyzed": total_trades
        }
