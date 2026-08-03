from bot.engine.voting import aggregate_signals

class MockConfig:
    strategy_weight_smc = 60
    strategy_weight_pattern = 60
    strategy_weight_news = 60
    strategy_weight_wyckoff = 50
    strategy_weight_sr_volume = 50
    strategy_weight_auto_pattern = 50
    strategy_weight_kill_zones = 50
    allow_single_strategy_trade = False

config = MockConfig()

print("=== Test 1: 3/7 kelishuvi ===")
res1 = aggregate_signals(
    smc_data={"signal": "BUY", "confidence": 65},
    pattern_data={"signal": "BUY", "confidence": 70},
    news_data={"signal": "BUY", "confidence": 80},
    wyckoff_data={},
    sr_volume_data={},
    auto_pattern_data={},
    kill_zones_data={},
    config=config
)
print(res1)
assert res1['signal'] == "BUY"
assert res1['risk_pct'] == 0.03

print("\n=== Test 2: SMC + News (Pattern ishlashni rad etdi) ===")
res2 = aggregate_signals(
    smc_data={"signal": "SELL", "confidence": 61},
    pattern_data={"signal": "HOLD", "confidence": 0},
    news_data={"signal": "SELL", "confidence": 90},
    wyckoff_data={},
    sr_volume_data={},
    auto_pattern_data={},
    kill_zones_data={},
    config=config
)
print(res2)
assert res2['signal'] == "SELL"
assert res2['risk_pct'] == 0.02

print("\n=== Test 3: SMC + Pattern (News kutishda) ===")
res3 = aggregate_signals(
    smc_data={"signal": "BUY", "confidence": 75},
    pattern_data={"signal": "BUY", "confidence": 65},
    news_data={"signal": "HOLD", "confidence": 50},
    wyckoff_data={},
    sr_volume_data={},
    auto_pattern_data={},
    kill_zones_data={},
    config=config
)
print(res3)
assert res3['signal'] == "BUY"
assert res3['risk_pct'] == 0.02

print("\n=== Test 4: Ziddiyat (SMC Buy, News Sell) ===")
res4 = aggregate_signals(
    smc_data={"signal": "BUY", "confidence": 75},
    pattern_data={"signal": "HOLD", "confidence": 0},
    news_data={"signal": "SELL", "confidence": 65},
    wyckoff_data={},
    sr_volume_data={},
    auto_pattern_data={},
    kill_zones_data={},
    config=config
)
print(res4)
assert res4['signal'] == "HOLD"
assert res4['risk_pct'] == 0.0

print("\n=== Test 5: Yakka strategiya (SMC faqat) ALLOW_SINGLE=False ===")
res5 = aggregate_signals(
    smc_data={"signal": "SELL", "confidence": 80},
    pattern_data={"signal": "HOLD", "confidence": 0},
    news_data={"signal": "HOLD", "confidence": 0},
    wyckoff_data={},
    sr_volume_data={},
    auto_pattern_data={},
    kill_zones_data={},
    config=config
)
print(res5)
assert res5['signal'] == "HOLD"
assert res5['risk_pct'] == 0.0

print("\nBarcha testlar muvaffaqiyatli o'tdi!")
