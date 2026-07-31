"""
AI Trading Bot — Entry Point.

Botni ishga tushirish uchun: python run_bot.py
To'xtash uchun: Ctrl+C
"""
import logging
import sys

# Configure stdout encoding for Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Logging sozlash
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)

from bot.main import create_bot


def main():
    bot = create_bot()
    bot.start()


if __name__ == "__main__":
    main()
