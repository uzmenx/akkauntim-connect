import sys
import os
sys.path.append(os.path.abspath('.'))

from bot.learning.trade_reviewer import TradeReviewer

print("TradeReviewer imported successfully!")

class MockMT5:
    pass

class MockAI:
    pass

config = {}

reviewer = TradeReviewer(MockMT5(), MockAI(), config)
print("TradeReviewer initialized successfully and DB schema created!")
