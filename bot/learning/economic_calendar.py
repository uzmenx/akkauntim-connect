import sqlite3
import os
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

class EconomicCalendarManager:
    def __init__(self, db_path='bot_learning.db'):
        # Root dir is 3 levels up from bot/learning/economic_calendar.py
        self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.db_path = os.path.join(self.root_dir, db_path)
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS economic_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_title TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    impact TEXT NOT NULL,
                    event_datetime TEXT NOT NULL,
                    actual TEXT,
                    forecast TEXT,
                    previous TEXT,
                    fetched_at TEXT NOT NULL,
                    UNIQUE(event_title, currency, event_datetime)
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_econ_curr_dt ON economic_events(currency, event_datetime)')
            conn.commit()
        except Exception as e:
            logger.error(f"Error initializing economic_events table: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    def fetch_calendar(self) -> int:
        """Fetch this week's calendar, parse XML, save to DB. Return count of events saved."""
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            events_to_insert = []
            now_iso = datetime.now(timezone.utc).isoformat()
            
            for event in root.findall('event'):
                title = event.findtext('title', default='').strip()
                currency = event.findtext('country', default='').strip()
                date_str = event.findtext('date', default='').strip()
                time_str = event.findtext('time', default='').strip()
                impact = event.findtext('impact', default='').strip()
                forecast = event.findtext('forecast', default='').strip()
                previous = event.findtext('previous', default='').strip()
                
                event_dt_iso = ""
                try:
                    if time_str.lower() in ["all day", "tentative", ""]:
                        dt = datetime.strptime(date_str, "%m-%d-%Y")
                        event_dt_iso = dt.isoformat()
                    else:
                        dt_str = f"{date_str} {time_str}"
                        dt = datetime.strptime(dt_str, "%m-%d-%Y %I:%M%p")
                        event_dt_iso = dt.isoformat()
                except ValueError:
                    logger.warning(f"Could not parse date/time for event {title}: {date_str} {time_str}")
                    continue
                
                events_to_insert.append((
                    title, currency, impact, event_dt_iso, forecast, previous, now_iso
                ))
                
            if not events_to_insert:
                return 0
                
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            inserted_count = 0
            for ev in events_to_insert:
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO economic_events 
                        (event_title, currency, impact, event_datetime, forecast, previous, fetched_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', ev)
                    inserted_count += cursor.rowcount
                except Exception as e:
                    logger.error(f"Error inserting event {ev[0]}: {e}")
            conn.commit()
            return inserted_count
        except Exception as e:
            logger.error(f"Failed to fetch or parse economic calendar: {e}")
            return 0
        finally:
            if 'conn' in locals():
                conn.close()

    def _should_refetch(self) -> bool:
        """True if last fetch was more than 6 hours ago."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT MAX(fetched_at) FROM economic_events')
            row = cursor.fetchone()
            if not row or not row[0]:
                return True
                
            last_fetch = datetime.fromisoformat(row[0])
            if last_fetch.tzinfo is None:
                last_fetch = last_fetch.replace(tzinfo=timezone.utc)
                
            if datetime.now(timezone.utc) - last_fetch > timedelta(hours=6):
                return True
            return False
        except Exception as e:
            logger.error(f"Error checking if should refetch: {e}")
            return True
        finally:
            if 'conn' in locals():
                conn.close()

    def get_upcoming_events(self, currency: str = None, hours: int = 24) -> list:
        """Get upcoming events for next N hours."""
        if self._should_refetch():
            self.fetch_calendar()
            
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            now_iso = datetime.now(timezone.utc).isoformat()
            target_iso = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
            
            query = '''
                SELECT * FROM economic_events 
                WHERE event_datetime >= ? AND event_datetime <= ?
            '''
            params = [now_iso, target_iso]
            
            if currency:
                query += ' AND currency = ?'
                params.append(currency)
                
            query += ' ORDER BY event_datetime ASC'
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching upcoming events: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()

    def is_safe_to_trade(self, symbol: str, hours_before: int = 4, hours_after: int = 1) -> dict:
        """Check if it's safe to trade given symbol."""
        if self._should_refetch():
            self.fetch_calendar()
            
        if len(symbol) == 6:
            currencies = [symbol[:3], symbol[3:]]
        else:
            currencies = [symbol]
            
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            now = datetime.now(timezone.utc)
            start_window = (now - timedelta(hours=hours_after)).isoformat()
            end_window = (now + timedelta(hours=hours_before)).isoformat()
            
            placeholders = ','.join('?' for _ in currencies)
            query = f'''
                SELECT * FROM economic_events 
                WHERE currency IN ({placeholders})
                AND event_datetime >= ? AND event_datetime <= ?
            '''
            params = currencies + [start_window, end_window]
            
            cursor.execute(query, params)
            events = cursor.fetchall()
            
            upcoming_events = []
            is_safe = True
            reason = "No high/medium impact events in the immediate window."
            
            for row in events:
                event = dict(row)
                upcoming_events.append(event)
                impact = event['impact'].lower()
                event_dt = datetime.fromisoformat(event['event_datetime'])
                if event_dt.tzinfo is None:
                    event_dt = event_dt.replace(tzinfo=timezone.utc)
                    
                if impact == 'high':
                    is_safe = False
                    reason = f"High impact event '{event['event_title']}' for {event['currency']} around {event['event_datetime']}."
                    break
                elif impact == 'medium' and event_dt <= (now + timedelta(hours=2)):
                    is_safe = False
                    reason = f"Medium impact event '{event['event_title']}' for {event['currency']} within 2 hours ({event['event_datetime']})."
                    break
                    
            return {
                'safe': is_safe,
                'reason': reason,
                'upcoming_events': upcoming_events
            }
        except Exception as e:
            logger.error(f"Error checking if safe to trade: {e}")
            return {'safe': False, 'reason': f"Error checking events: {e}", 'upcoming_events': []}
        finally:
            if 'conn' in locals():
                conn.close()
