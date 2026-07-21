"""
AI Trading Bot — Entry Point.

Botni ishga tushirish uchun: python run_bot.py
To'xtash uchun: Ctrl+C
"""
import logging

# Logging sozlash
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

from bot.main import create_bot


def main():
    bot = create_bot()
    bot.start()


if __name__ == "__main__":
    main()
