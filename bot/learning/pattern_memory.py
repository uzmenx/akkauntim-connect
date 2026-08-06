import sqlite3
import json
import logging
import os
import datetime
import math

logger = logging.getLogger(__name__)

class PatternMemoryBank:
    def __init__(self, db_path='bot_learning.db'):
        try:
            # root_dir -> bot/learning -> bot -> ac
            self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.db_path = os.path.join(self.root_dir, db_path)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            self._init_db()
        except Exception as e:
            logger.error(f"Failed to initialize PatternMemoryBank: {e}")

    def _init_db(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pattern_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    pattern_vector TEXT NOT NULL,
                    candle_count INTEGER NOT NULL,
                    atr_at_entry REAL,
                    smc_zone_type TEXT,
                    outcome TEXT NOT NULL,
                    pnl REAL DEFAULT 0.0,
                    metadata TEXT
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_pm_sym_dir 
                ON pattern_memory(symbol, direction, outcome)
            ''')
            conn.commit()
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
        finally:
            if conn:
                conn.close()

    def _encode_candles(self, candles: list, atr: float) -> list:
        """Encode last 5 candles into normalized feature vector."""
        features = []
        try:
            target_candles = candles[-5:] if candles else []
            
            for c in target_candles:
                o = float(c.get('open', 0.0))
                h = float(c.get('high', 0.0))
                l = float(c.get('low', 0.0))
                cl = float(c.get('close', 0.0))
                
                hl = max(h - l, 1e-10)
                safe_atr = max(atr, 1e-10)
                
                body_ratio = (cl - o) / hl
                upper_wick = (h - max(o, cl)) / hl
                lower_wick = (min(o, cl) - l) / hl
                range_vs_atr = (h - l) / safe_atr
                close_position = (cl - l) / hl
                
                features.extend([
                    round(body_ratio, 6),
                    round(upper_wick, 6),
                    round(lower_wick, 6),
                    round(range_vs_atr, 6),
                    round(close_position, 6)
                ])
                
            # Pad with zeros if less than 5 candles
            while len(features) < 25:
                features.append(0.0)
                
        except Exception as e:
            logger.error(f"Error encoding candles: {e}")
            while len(features) < 25:
                features.append(0.0)
                
        return features

    def _cosine_similarity(self, a: list, b: list) -> float:
        try:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x**2 for x in a) ** 0.5
            norm_b = sum(x**2 for x in b) ** 0.5
            if norm_a < 1e-10 or norm_b < 1e-10:
                return 0.0
            return dot / (norm_a * norm_b)
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0

    def record_pattern(self, symbol, timeframe, direction, candles, atr, smc_zone_type, outcome, pnl, metadata=None):
        """Record a trade pattern (called when trade closes)."""
        conn = None
        try:
            pattern_vector = self._encode_candles(candles, atr)
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            meta_json = json.dumps(metadata) if metadata else None
            vec_json = json.dumps(pattern_vector)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO pattern_memory (
                    timestamp, symbol, timeframe, direction, pattern_vector, 
                    candle_count, atr_at_entry, smc_zone_type, outcome, pnl, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                now, symbol, timeframe, direction, vec_json, 
                len(candles), atr, smc_zone_type, outcome, pnl, meta_json
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Error recording pattern: {e}")
        finally:
            if conn:
                conn.close()

    def find_similar_patterns(self, symbol, direction, candles, atr, top_k=5) -> list:
        """Find top_k most similar WIN patterns using cosine similarity."""
        conn = None
        results = []
        try:
            current_vector = self._encode_candles(candles, atr)
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Load all WIN patterns for this symbol and direction
            cursor.execute('''
                SELECT * FROM pattern_memory 
                WHERE symbol = ? AND direction = ? AND outcome = 'WIN'
            ''', (symbol, direction))
            
            rows = cursor.fetchall()
            
            matches = []
            for row in rows:
                stored_vector = json.loads(row['pattern_vector'])
                sim = self._cosine_similarity(current_vector, stored_vector)
                
                match_data = dict(row)
                match_data['similarity'] = round(sim, 6)
                # Remove raw vector from results to save memory
                match_data.pop('pattern_vector', None)
                matches.append(match_data)
                
            matches.sort(key=lambda x: x['similarity'], reverse=True)
            results = matches[:top_k]
            
        except Exception as e:
            logger.error(f"Error finding similar patterns: {e}")
        finally:
            if conn:
                conn.close()
                
        return results

    def get_confidence_adjustment(self, symbol, direction, candles, atr) -> dict:
        """Get confidence adjustment based on pattern similarity."""
        result = {
            'adjustment': 0.0,
            'match_count': 0,
            'avg_similarity': 0.0,
            'reasoning': 'No matches found.'
        }
        
        conn = None
        try:
            current_vector = self._encode_candles(candles, atr)
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT pattern_vector, outcome 
                FROM pattern_memory 
                WHERE symbol = ? AND direction = ?
            ''', (symbol, direction))
            
            rows = cursor.fetchall()
            
            matches = []
            for row in rows:
                stored_vector = json.loads(row['pattern_vector'])
                sim = self._cosine_similarity(current_vector, stored_vector)
                matches.append({'similarity': sim, 'outcome': row['outcome']})
                
            matches.sort(key=lambda x: x['similarity'], reverse=True)
            top_matches = matches[:3]
            
            if not top_matches:
                return result
                
            result['match_count'] = len(top_matches)
            avg_sim = sum(m['similarity'] for m in top_matches) / len(top_matches)
            result['avg_similarity'] = round(avg_sim, 4)
            
            win_count = sum(1 for m in top_matches if m['outcome'] == 'WIN')
            loss_count = len(top_matches) - win_count
            
            if avg_sim < 0.50:
                result['adjustment'] = 0.0
                result['reasoning'] = 'Low similarity to past patterns.'
            elif avg_sim > 0.85 and win_count == len(top_matches):
                result['adjustment'] = 0.15
                result['reasoning'] = 'Strong match with past winning patterns.'
            elif avg_sim > 0.70 and win_count >= loss_count:
                result['adjustment'] = 0.08
                result['reasoning'] = 'Good match with predominantly winning patterns.'
            elif avg_sim > 0.60 and loss_count > win_count:
                result['adjustment'] = -0.10
                result['reasoning'] = 'Moderate match with predominantly losing patterns.'
            else:
                result['adjustment'] = 0.0
                result['reasoning'] = 'Mixed historical outcomes for similar patterns.'
                
        except Exception as e:
            logger.error(f"Error calculating confidence adjustment: {e}")
        finally:
            if conn:
                conn.close()
                
        return result

    def get_stats(self) -> dict:
        """Return pattern memory statistics."""
        stats = {
            'total_patterns': 0,
            'win_patterns': 0,
            'loss_patterns': 0,
            'symbols': []
        }
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT outcome, COUNT(*) FROM pattern_memory GROUP BY outcome")
            for outcome, count in cursor.fetchall():
                stats['total_patterns'] += count
                if outcome == 'WIN':
                    stats['win_patterns'] = count
                elif outcome == 'LOSS':
                    stats['loss_patterns'] = count
                    
            cursor.execute("SELECT DISTINCT symbol FROM pattern_memory")
            stats['symbols'] = [row[0] for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Error fetching stats: {e}")
        finally:
            if conn:
                conn.close()
                
        return stats
