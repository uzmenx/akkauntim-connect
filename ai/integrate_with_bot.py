"""
Example integration hook to call the inference from the MT5 trading bot.
Adapt get_market_context() to use your bot's candles/indicators.
"""

from ai.deepseek_inference import generate_signal
from ai.prompt_templates import GENERIC_TEMPLATE
import time


def get_market_context(symbol: str, timeframe: str, n_candles: int = 50) -> str:
    """
    Replace this with actual extraction from your MT5 structures.
    Return a textual representation that includes recent OHLC and indicators.
    """
    # TODO: integrate with your MT5 data structures
    return f"SYMBOL: {symbol}\nTF: {timeframe}\nCANDLES: []\nINDICATORS: []"


def run_signal_cycle(symbol: str, timeframe: str):
    context = get_market_context(symbol, timeframe)
    result = generate_signal(context, prompt_template=GENERIC_TEMPLATE)
    parsed = result.get('parsed')
    if isinstance(parsed, dict):
        signal = parsed.get('signal')
        conf = parsed.get('confidence')
        reason = parsed.get('reason')
        print(f"[{symbol}] signal={signal} conf={conf} reason={reason}")
        # TODO: integrate decision logic (risk mgmt, sizing, order placement)
    else:
        print('Model returned unexpected output:', result.get('raw'))


if __name__ == '__main__':
    # simple loop example
    while True:
        run_signal_cycle('EURUSD', 'M5')
        time.sleep(30)
