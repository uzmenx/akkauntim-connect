"""
news_detector.py
================
Fetches economic calendar events to be used as a Fundamental Strategy trigger.
Uses the free open JSON endpoint from Forex Factory.
Supports historical news, real-time polling, and AI analysis formatting.
"""

import requests
import pandas as pd
from datetime import datetime, timezone
import dateutil.parser
import json
import os
import time

class NewsDetector:
    def __init__(self, target_currencies=None):
        self.target_currencies = target_currencies or ["USD", "EUR", "GBP", "JPY"]
        self.calendar_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        self.cache_file = "news_cache.json"
        self.cache_duration = 43200  # 12 soat (sekundlarda)
        self.events = []
    
    def fetch_calendar(self, force_refresh=False):
        """Fetches the latest economic calendar events for this week"""
        # 1. Kesh faylni tekshiramiz
        if os.path.exists(self.cache_file) and not force_refresh:
            file_age = time.time() - os.path.getmtime(self.cache_file)
            if file_age < self.cache_duration:
                try:
                    with open(self.cache_file, 'r', encoding='utf-8') as f:
                        self.events = json.load(f)
                    return True
                except Exception as e:
                    print(f"Error reading news cache: {e}")
        
        # 2. Agar kesh eski bo'lsa yoki yo'q bo'lsa API dan tortamiz
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(self.calendar_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self.events = data
            
            # 3. Muvaffaqiyatli tortilsa keshga yozib qo'yamiz
            try:
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f)
            except Exception as e:
                print(f"Error writing news cache: {e}")
                
            return True
        except Exception as e:
            print(f"Error fetching news calendar: {e}")
            # Agar API 429 xatolik bersa (limitga tushsa), lekin eski kesh bo'lsa
            if os.path.exists(self.cache_file):
                try:
                    with open(self.cache_file, 'r', encoding='utf-8') as f:
                        self.events = json.load(f)
                    return True
                except:
                    pass
            return False

    def get_news_history(self, hours_back=24):
        """
        Returns a list of news events that occurred in the past `hours_back` hours.
        Includes Actual, Forecast, and Previous values to evaluate impact.
        """
        if not self.events:
            self.fetch_calendar()
            
        now = datetime.now(timezone.utc)
        history = []
        
        for event in self.events:
            country = event.get('country')
            if country not in self.target_currencies:
                continue
                
            event_date_str = event.get('date')
            if not event_date_str:
                continue
                
            try:
                event_date = dateutil.parser.isoparse(event_date_str)
                event_date_utc = event_date.astimezone(timezone.utc)
                
                delta = now - event_date_utc
                delta_hours = delta.total_seconds() / 3600.0
                
                # If event happened in the past up to `hours_back`
                if 0 <= delta_hours <= hours_back:
                    event_copy = event.copy()
                    event_copy['hours_ago'] = round(delta_hours, 1)
                    history.append(event_copy)
            except Exception:
                pass
                
        # Sort so that the most recent news is first
        history.sort(key=lambda x: x.get('hours_ago', 0))
        return history

    def get_upcoming_news(self, impact_filter=None, minutes_ahead=60):
        """
        Returns a list of news events happening within the next `minutes_ahead` minutes.
        """
        if not self.events:
            self.fetch_calendar()
            
        now = datetime.now(timezone.utc)
        upcoming = []
        
        for event in self.events:
            country = event.get('country')
            impact = event.get('impact')
            
            if country not in self.target_currencies:
                continue
                
            if impact_filter and impact not in impact_filter:
                continue
                
            event_date_str = event.get('date')
            if not event_date_str:
                continue
                
            try:
                event_date = dateutil.parser.isoparse(event_date_str)
                event_date_utc = event_date.astimezone(timezone.utc)
                
                delta = event_date_utc - now
                delta_minutes = delta.total_seconds() / 60.0
                
                if 0 <= delta_minutes <= minutes_ahead:
                    event_copy = event.copy()
                    event_copy['minutes_to_release'] = round(delta_minutes, 1)
                    upcoming.append(event_copy)
            except Exception:
                pass
                
        upcoming.sort(key=lambda x: x.get('minutes_to_release', 999))
        return upcoming

    def format_news_for_ai(self, hours_back=24, minutes_ahead=180):
        """
        Formats recent historical news and upcoming news into a clean text prompt
        for Claude AI to perform fundamental analysis.
        """
        recent = self.get_news_history(hours_back=hours_back)
        upcoming = self.get_upcoming_news(minutes_ahead=minutes_ahead)
        
        text = "=== FUNDAMENTAL NEWS ANALYSIS ===\n"
        
        text += f"\nYaqinda (so'nggi {hours_back} soatda) e'lon qilingan yangiliklar:\n"
        if recent:
            for e in recent:
                actual = e.get('actual', 'N/A')
                forecast = e.get('forecast', 'N/A')
                prev = e.get('previous', 'N/A')
                text += f"- [{e['impact']}] {e['country']} | {e['title']} ({e['hours_ago']} soat oldin)\n"
                text += f"  Haqiqiy (Actual): {actual} | Prognoz (Forecast): {forecast} | Oldingi (Previous): {prev}\n"
        else:
            text += "- Yaqin orada hech qanday muhim yangilik e'lon qilinmadi.\n"
            
        text += f"\nYaqin orada (kelgusi {round(minutes_ahead/60, 1)} soatda) kutilayotgan yangiliklar:\n"
        if upcoming:
            for e in upcoming:
                forecast = e.get('forecast', 'N/A')
                prev = e.get('previous', 'N/A')
                text += f"- [{e['impact']}] {e['country']} | {e['title']} (yana {e['minutes_to_release']} daqiqadan so'ng)\n"
                text += f"  Prognoz (Forecast): {forecast} | Oldingi (Previous): {prev}\n"
        else:
            text += "- Yaqin soatlar ichida hech qanday muhim yangilik kutilmayapti.\n"
            
        return text

if __name__ == "__main__":
    detector = NewsDetector()
    print(detector.format_news_for_ai(hours_back=72, minutes_ahead=1440))
