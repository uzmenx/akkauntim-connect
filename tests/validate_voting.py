from bot.engine.voting import aggregate_signals

print("=== Test 1: 3/3 kelishuvi ===")
res1 = aggregate_signals(
    {"signal": "BUY", "confidence": 65},
    {"signal": "BUY", "confidence": 70},
    {"signal": "BUY", "confidence": 80}
)
print(res1)
assert res1['signal'] == "BUY"
assert res1['risk_pct'] == 0.04

print("\n=== Test 2: SMC + News (Pattern ishlashni rad etdi) ===")
res2 = aggregate_signals(
    {"signal": "SELL", "confidence": 61},
    {"signal": "HOLD", "confidence": 0},
    {"signal": "SELL", "confidence": 90}
)
print(res2)
assert res2['signal'] == "SELL"
assert res2['risk_pct'] == 0.03

print("\n=== Test 3: SMC + Pattern (News kutishda) ===")
res3 = aggregate_signals(
    {"signal": "BUY", "confidence": 75},
    {"signal": "BUY", "confidence": 65},
    {"signal": "HOLD", "confidence": 50}
)
print(res3)
assert res3['signal'] == "BUY"
assert res3['risk_pct'] == 0.02

print("\n=== Test 4: Ziddiyat (SMC Buy, News Sell) ===")
res4 = aggregate_signals(
    {"signal": "BUY", "confidence": 75},
    {"signal": "HOLD", "confidence": 0},
    {"signal": "SELL", "confidence": 65}
)
print(res4)
assert res4['signal'] == "HOLD"
assert res4['risk_pct'] == 0.0

print("\n=== Test 5: Yakka strategiya (SMC faqat) ALLOW_SINGLE=False ===")
res5 = aggregate_signals(
    {"signal": "SELL", "confidence": 80},
    {"signal": "HOLD", "confidence": 0},
    {"signal": "HOLD", "confidence": 0}
)
print(res5)
assert res5['signal'] == "HOLD"
assert res5['risk_pct'] == 0.0

print("\nBarcha testlar muvaffaqiyatli o'tdi!")
