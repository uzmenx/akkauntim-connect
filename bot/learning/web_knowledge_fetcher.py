"""
web_knowledge_fetcher.py — Shadow AI Web Auto-Learning Pipeline

Shadow AI internetdan avtomatik bilim to'playdi:
1. DuckDuckGo orqali trading strategiyalar qidiradi
2. Forex Factory / FXStreet RSS feedlarini o'qiydi
3. Topilgan bilimlarni AIStrategist → ChromaDB pipeline orqali saqlaydi
4. AIMemory ga saboqlar qo'shadi

Production-grade: rate-limiting, cache, error-handling, audit trail.
"""

import os
import json
import sqlite3
import hashlib
import logging
import time
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Optional dependencies — graceful degradation
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests kutubxonasi topilmadi. pip install requests")

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    logger.warning("feedparser kutubxonasi topilmadi. pip install feedparser")

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    logger.warning("duckduckgo_search kutubxonasi topilmadi. pip install duckduckgo-search")


# ==================== KONFIGURATSIYA ====================

# Qidiruv mavzulari — har safar birini tanlaydi
TRADING_SEARCH_TOPICS = [
    "forex trading strategy SMC order block entry",
    "institutional order flow trading setup",
    "supply demand zone forex strategy 2025",
    "smart money concept trading rules",
    "wyckoff accumulation distribution trading",
    "harmonic pattern bat gartley forex",
    "forex liquidity grab stop hunt strategy",
    "break of structure market structure shift",
    "forex risk management position sizing rules",
    "price action trading pin bar engulfing",
    "forex trend following moving average strategy",
    "support resistance breakout pullback trading",
    "EURUSD GBPUSD XAUUSD technical analysis",
    "forex kill zone London New York session trading",
    "fair value gap imbalance trading strategy",
]

# RSS feed manbalari
RSS_FEEDS = {
    "forex_factory": "https://www.forexfactory.com/rss",
    "fxstreet_news": "https://www.fxstreet.com/rss/news",
    "fxstreet_analysis": "https://www.fxstreet.com/rss/technical-analysis",
    "dailyfx": "https://www.dailyfx.com/feeds/market-news",
    "investing_forex": "https://www.investing.com/rss/news_301.rss",
}

# Rate limiting
MIN_FETCH_INTERVAL_SECONDS = 7200  # 2 soat
MAX_RESULTS_PER_SEARCH = 8
REQUEST_TIMEOUT = 20
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ShadowAI/2.0 TradingBot"


class WebKnowledgeFetcher:
    """
    Internetdan trading bilim to'playdigan modul.
    AIStrategist va AIMemory bilan integratsiya qiladi.
    """

    def __init__(self, db_path: str = 'bot_learning.db', 
                 ai_strategist=None, ai_memory=None):
        """
        Args:
            db_path: SQLite bazasi yo'li
            ai_strategist: AIStrategist instance (ChromaDB pipeline uchun)
            ai_memory: AIMemory instance (saboqlar uchun)
        """
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if not os.path.isabs(db_path):
            self.db_path = os.path.join(root_dir, db_path)
        else:
            self.db_path = db_path

        self.ai_strategist = ai_strategist
        self.ai_memory = ai_memory
        self._topic_index = 0  # Round-robin topic selection
        self._init_db()

    def _init_db(self):
        """Web knowledge cache jadvalini yaratish."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS web_knowledge_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_hash TEXT UNIQUE NOT NULL,
                    source_type TEXT NOT NULL,
                    source_url TEXT,
                    title TEXT,
                    content_snippet TEXT,
                    processed INTEGER DEFAULT 0,
                    insights_extracted INTEGER DEFAULT 0,
                    fetched_at TEXT NOT NULL,
                    processed_at TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS web_fetch_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fetch_type TEXT NOT NULL,
                    topic TEXT,
                    results_count INTEGER DEFAULT 0,
                    insights_saved INTEGER DEFAULT 0,
                    duration_sec REAL,
                    status TEXT,
                    error_message TEXT,
                    timestamp TEXT NOT NULL
                )
            ''')

            cursor.execute('CREATE INDEX IF NOT EXISTS idx_wkc_hash ON web_knowledge_cache(content_hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_wkc_processed ON web_knowledge_cache(processed)')

            conn.commit()
        except Exception as e:
            logger.error(f"WebKnowledgeFetcher DB init xatolik: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    # ==================== MANBA 1: DUCKDUCKGO SEARCH ====================

    def _search_duckduckgo(self, topic: str, max_results: int = 8) -> List[Dict[str, str]]:
        """DuckDuckGo orqali trading mavzular bo'yicha qidirish."""
        if not DDGS_AVAILABLE:
            logger.warning("DuckDuckGo search mavjud emas.")
            return []

        results = []
        try:
            with DDGS() as ddgs:
                search_results = ddgs.text(
                    topic, 
                    max_results=max_results,
                    region='wt-wt',  # worldwide
                    safesearch='off'
                )
                for r in search_results:
                    results.append({
                        "title": r.get("title", ""),
                        "body": r.get("body", ""),
                        "url": r.get("href", ""),
                        "source": "duckduckgo"
                    })
            logger.info(f"DuckDuckGo: '{topic[:40]}...' → {len(results)} natija")
        except Exception as e:
            logger.error(f"DuckDuckGo qidiruvda xatolik: {e}")

        return results

    # ==================== MANBA 2: RSS FEEDS ====================

    def _fetch_rss_feed(self, feed_name: str, feed_url: str, max_entries: int = 10) -> List[Dict[str, str]]:
        """RSS feed dan yangiliklar o'qish."""
        if not FEEDPARSER_AVAILABLE:
            logger.warning("feedparser mavjud emas.")
            return []

        results = []
        try:
            feed = feedparser.parse(feed_url, request_headers={
                'User-Agent': USER_AGENT
            })

            if feed.bozo and not feed.entries:
                logger.warning(f"RSS feed '{feed_name}' parseda xatolik: {feed.bozo_exception}")
                return []

            for entry in feed.entries[:max_entries]:
                title = entry.get('title', '')
                summary = entry.get('summary', entry.get('description', ''))
                link = entry.get('link', '')

                # HTML teglarini tozalash
                summary = re.sub(r'<[^>]+>', '', summary).strip()

                if len(summary) < 50:
                    continue  # Juda qisqa kontent

                results.append({
                    "title": title,
                    "body": summary[:2000],  # Max 2000 belgi
                    "url": link,
                    "source": f"rss_{feed_name}"
                })

            logger.info(f"RSS '{feed_name}': {len(results)} maqola o'qildi")
        except Exception as e:
            logger.error(f"RSS feed '{feed_name}' o'qishda xatolik: {e}")

        return results

    def _fetch_all_rss(self) -> List[Dict[str, str]]:
        """Barcha RSS feedlardan ma'lumot to'plash."""
        all_results = []
        for name, url in RSS_FEEDS.items():
            try:
                results = self._fetch_rss_feed(name, url, max_entries=5)
                all_results.extend(results)
                time.sleep(1)  # Rate limiting — har feed orasida 1 sek
            except Exception as e:
                logger.error(f"RSS '{name}' da xatolik: {e}")
                continue
        return all_results

    # ==================== MANBA 3: WEB PAGE CONTENT ====================

    def _fetch_page_content(self, url: str) -> Optional[str]:
        """Web sahifadan matn kontentini olish (oddiy HTML parse)."""
        if not REQUESTS_AVAILABLE:
            return None
        
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers={
                'User-Agent': USER_AGENT
            })
            resp.raise_for_status()

            text = resp.text
            # HTML teglarini tozalash (oddiy regex — BeautifulSoup shart emas)
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()

            # Faqat foydali qismini olish (o'rtacha 500-4000 belgi)
            if len(text) > 4000:
                text = text[:4000]
            if len(text) < 100:
                return None

            return text
        except Exception as e:
            logger.debug(f"Sahifa kontentini olishda xatolik ({url[:60]}): {e}")
            return None

    # ==================== CACHE VA DEDUPLIKATSIYA ====================

    def _content_hash(self, content: str) -> str:
        """Kontent hashini hisoblash (dublikat oldini olish uchun)."""
        normalized = content.lower().strip()[:500]
        return hashlib.md5(normalized.encode('utf-8', errors='ignore')).hexdigest()

    def _is_cached(self, content_hash: str) -> bool:
        """Bu kontent allaqachon bazada bormi?"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM web_knowledge_cache WHERE content_hash = ?",
                (content_hash,)
            )
            count = cursor.fetchone()[0]
            return count > 0
        except Exception:
            return False
        finally:
            if 'conn' in locals():
                conn.close()

    def _save_to_cache(self, content_hash: str, source_type: str, 
                        url: str, title: str, snippet: str) -> bool:
        """Yangi kontentni cache ga saqlash."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO web_knowledge_cache 
                (content_hash, source_type, source_url, title, content_snippet, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (content_hash, source_type, url, title, snippet[:2000],
                  datetime.now().isoformat()))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Cache saqlashda xatolik: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()

    def _mark_processed(self, content_hash: str, insights_count: int):
        """Kontent qayta ishlanganligi haqida belgi qo'yish."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE web_knowledge_cache 
                SET processed = 1, insights_extracted = ?, processed_at = ?
                WHERE content_hash = ?
            ''', (insights_count, datetime.now().isoformat(), content_hash))
            conn.commit()
        except Exception as e:
            logger.error(f"Cache yangilashda xatolik: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    # ==================== ASOSIY PIPELINE ====================

    def _process_content_to_knowledge(self, title: str, content: str, 
                                        source: str, url: str) -> int:
        """
        Topilgan kontentni AIStrategist pipeline orqali ChromaDB ga qo'shish.
        LLM ishlatmaydi — faqat toza faktlarni saqlaydi.
        
        Returns: Saqlangan insights soni
        """
        content_hash = self._content_hash(content)
        
        if self._is_cached(content_hash):
            return 0

        # Cache ga saqlash
        self._save_to_cache(content_hash, source, url, title, content)

        insights_saved = 0

        # 1. AIStrategist orqali ChromaDB ga qo'shish (LLM bilan)
        if self.ai_strategist:
            try:
                # _process_source ni to'g'ridan-to'g'ri chaqiramiz
                # Avval knowledge_sources ga yozish
                conn = sqlite3.connect(self.ai_strategist.db_path, timeout=30.0)
                cursor = conn.cursor()

                try:
                    cursor.execute('''
                        INSERT INTO knowledge_sources 
                        (title, author, language, file_path, content_hash, category, added_date, processed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                    ''', (title[:200], f"web_{source}", "en", url, content_hash,
                          "web_article", datetime.now().isoformat()))
                    source_id = cursor.lastrowid
                    conn.commit()
                except sqlite3.IntegrityError:
                    # Allaqachon bor
                    logger.debug(f"Knowledge source allaqachon mavjud: {title[:60]}")
                    conn.close()
                    self._mark_processed(content_hash, 0)
                    return 0
                finally:
                    conn.close()

                # AIStrategist._process_source orqali LLM tahlili
                result = self.ai_strategist._process_source(source_id, content)
                if result and isinstance(result, tuple):
                    insights_saved = result[1] if len(result) > 1 else 0
                elif result:
                    insights_saved = 1

                logger.info(f"Web → ChromaDB: '{title[:50]}' → {insights_saved} insight")
            except Exception as e:
                logger.error(f"AIStrategist pipeline xatolik: {e}")

        # 2. AIMemory ga saboq sifatida qo'shish (oddiy matn)
        if self.ai_memory and len(content) > 100:
            try:
                # Matn qisqacha bo'lsa to'g'ridan-to'g'ri saqlash
                lesson_text = f"[Web] {title}: {content[:300]}"
                self.ai_memory.add_lesson(
                    lesson_text=lesson_text,
                    category="book_knowledge",
                    importance=3,
                    source="web_auto"
                )
            except Exception as e:
                logger.debug(f"AIMemory ga saqlashda xatolik: {e}")

        self._mark_processed(content_hash, insights_saved)
        return insights_saved

    def _get_next_topic(self) -> str:
        """Round-robin tarzda keyingi qidiruv mavzusini tanlash."""
        topic = TRADING_SEARCH_TOPICS[self._topic_index % len(TRADING_SEARCH_TOPICS)]
        self._topic_index += 1
        return topic

    def _should_fetch(self) -> bool:
        """Oxirgi fetchdan yetarli vaqt o'tdimi?"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp FROM web_fetch_log 
                WHERE status = 'success'
                ORDER BY id DESC LIMIT 1
            ''')
            row = cursor.fetchone()
            if not row:
                return True

            last_fetch = datetime.fromisoformat(row[0])
            elapsed = (datetime.now() - last_fetch).total_seconds()
            return elapsed >= MIN_FETCH_INTERVAL_SECONDS
        except Exception:
            return True
        finally:
            if 'conn' in locals():
                conn.close()

    def _log_fetch(self, fetch_type: str, topic: str, results_count: int,
                    insights_saved: int, duration: float, status: str,
                    error_msg: str = ""):
        """Fetch natijasini log ga yozish."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO web_fetch_log 
                (fetch_type, topic, results_count, insights_saved, duration_sec, status, error_message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (fetch_type, topic[:200] if topic else "", results_count,
                  insights_saved, round(duration, 2), status, error_msg,
                  datetime.now().isoformat()))
            conn.commit()
        except Exception as e:
            logger.error(f"Fetch log yozishda xatolik: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    # ==================== PUBLIC API ====================

    def fetch_and_learn(self, topic: Optional[str] = None, 
                        include_rss: bool = True) -> Dict[str, Any]:
        """
        Internetdan bilim to'plash va o'rganish.
        
        Args:
            topic: Qidiruv mavzusi (None bo'lsa avtomatik tanlanadi)
            include_rss: RSS feedlarni ham o'qish
            
        Returns:
            Natija hisoboti dict
        """
        start_time = time.time()
        report = {
            "status": "failed",
            "search_results": 0,
            "rss_results": 0,
            "new_content": 0,
            "insights_saved": 0,
            "duration_sec": 0,
            "topic": "",
            "timestamp": datetime.now().isoformat()
        }

        try:
            # 1. DuckDuckGo Search
            search_topic = topic or self._get_next_topic()
            report["topic"] = search_topic

            search_results = self._search_duckduckgo(search_topic, MAX_RESULTS_PER_SEARCH)
            report["search_results"] = len(search_results)

            total_insights = 0
            new_content = 0

            for result in search_results:
                title = result.get("title", "")
                body = result.get("body", "")
                url = result.get("url", "")

                if len(body) < 50:
                    continue

                # Sahifa kontentini olish (body qisqa bo'lsa)
                full_content = body
                if len(body) < 200 and url:
                    page_content = self._fetch_page_content(url)
                    if page_content:
                        full_content = page_content
                    time.sleep(0.5)  # Rate limit

                insights = self._process_content_to_knowledge(
                    title=title, content=full_content,
                    source="duckduckgo", url=url
                )
                total_insights += insights
                if insights > 0:
                    new_content += 1

            # 2. RSS Feeds
            if include_rss:
                rss_results = self._fetch_all_rss()
                report["rss_results"] = len(rss_results)

                for result in rss_results:
                    title = result.get("title", "")
                    body = result.get("body", "")
                    url = result.get("url", "")

                    if len(body) < 50:
                        continue

                    insights = self._process_content_to_knowledge(
                        title=title, content=body,
                        source=result.get("source", "rss"), url=url
                    )
                    total_insights += insights
                    if insights > 0:
                        new_content += 1

            duration = time.time() - start_time
            report["new_content"] = new_content
            report["insights_saved"] = total_insights
            report["duration_sec"] = round(duration, 2)
            report["status"] = "success"

            self._log_fetch("full", search_topic, 
                          report["search_results"] + report["rss_results"],
                          total_insights, duration, "success")

            logger.info(
                f"Web Auto-Learning yakunlandi: {new_content} yangi kontent, "
                f"{total_insights} insight, {duration:.1f}s"
            )

        except Exception as e:
            duration = time.time() - start_time
            report["duration_sec"] = round(duration, 2)
            report["status"] = "error"
            logger.error(f"Web Auto-Learning xatolik: {e}")
            self._log_fetch("full", report.get("topic", ""), 0, 0, 
                          duration, "error", str(e))

        return report

    def scheduled_fetch(self) -> Optional[Dict[str, Any]]:
        """
        Jadval bo'yicha fetch — faqat interval o'tgan bo'lsa ishlaydi.
        main.py dagi loop dan chaqiriladi.
        
        Returns:
            None agar hali erta bo'lsa, report dict agar ishlasa
        """
        if not self._should_fetch():
            return None

        logger.info("Web Auto-Learning scheduled fetch boshlanmoqda...")
        return self.fetch_and_learn(include_rss=True)

    def search_specific_topic(self, topic: str) -> Dict[str, Any]:
        """
        Aniq bir mavzu bo'yicha qidirish (manual trigger).
        Rate-limit tekshirmaydi.
        """
        return self.fetch_and_learn(topic=topic, include_rss=False)

    def get_fetch_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch tarixini olish."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT fetch_type, topic, results_count, insights_saved, 
                       duration_sec, status, timestamp
                FROM web_fetch_log 
                ORDER BY id DESC LIMIT ?
            ''', (limit,))

            history = []
            for row in cursor.fetchall():
                history.append({
                    "type": row[0],
                    "topic": row[1],
                    "results": row[2],
                    "insights": row[3],
                    "duration": row[4],
                    "status": row[5],
                    "timestamp": row[6]
                })
            return history
        except Exception as e:
            logger.error(f"Fetch tarixini olishda xatolik: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Web knowledge statistikasi."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM web_knowledge_cache")
            total_cached = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM web_knowledge_cache WHERE processed = 1")
            total_processed = cursor.fetchone()[0]

            cursor.execute("SELECT SUM(insights_extracted) FROM web_knowledge_cache WHERE processed = 1")
            total_insights = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(*) FROM web_fetch_log WHERE status = 'success'")
            total_fetches = cursor.fetchone()[0]

            cursor.execute('''
                SELECT source_type, COUNT(*) 
                FROM web_knowledge_cache 
                GROUP BY source_type
            ''')
            by_source = dict(cursor.fetchall())

            return {
                "total_cached": total_cached,
                "total_processed": total_processed,
                "total_insights": total_insights,
                "total_fetches": total_fetches,
                "by_source": by_source
            }
        except Exception as e:
            logger.error(f"Web stats olishda xatolik: {e}")
            return {}
        finally:
            if 'conn' in locals():
                conn.close()
