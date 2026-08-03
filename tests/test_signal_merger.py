from bot.prediction.signal_merger import merge_signals, compute_lstm_weight

def test_agreement_increases_confidence():
    # Both BUY
    res = merge_signals(
        symbol="EURUSD", timeframe="H1",
        voting_direction="BUY", voting_confidence=0.6,
        lstm_direction="UP", lstm_confidence=80,
        shadow_win_rate=0.7, shadow_trade_count=50
    )
    assert res.direction == "BUY"
    assert res.confidence > 0.6
    assert res.agreement is True
    print("test_agreement_increases_confidence passed")

def test_disagreement_decreases_confidence():
    # BUY vs DOWN
    res = merge_signals(
        symbol="EURUSD", timeframe="H1",
        voting_direction="BUY", voting_confidence=0.6,
        lstm_direction="DOWN", lstm_confidence=80,
        shadow_win_rate=0.7, shadow_trade_count=50
    )
    assert res.confidence < 0.6
    assert res.agreement is False
    print("test_disagreement_decreases_confidence passed")

def test_untrusted_lstm_has_low_weight():
    weight = compute_lstm_weight(
        symbol="EURUSD", timeframe="H1",
        shadow_win_rate=0.9, actual_trades=5, default_max_weight=0.35
    )
    assert weight < 0.05  # Very low weight
    print("test_untrusted_lstm_has_low_weight passed")

def test_poor_lstm_history_suppressed():
    weight = compute_lstm_weight(
        symbol="EURUSD", timeframe="H1",
        shadow_win_rate=0.4, actual_trades=50, default_max_weight=0.35
    )
    assert weight == 0.0
    print("test_poor_lstm_history_suppressed passed")

def test_lstm_never_flips_direction_alone():
    # Voting strong BUY, LSTM strong DOWN, but LSTM weight is capped
    res = merge_signals(
        symbol="EURUSD", timeframe="H1",
        voting_direction="BUY", voting_confidence=0.8,
        lstm_direction="DOWN", lstm_confidence=99,
        shadow_win_rate=0.8, shadow_trade_count=100
    )
    assert res.direction == "BUY" or res.direction == "NEUTRAL"
    assert res.agreement is False
    print("test_lstm_never_flips_direction_alone passed")

def test_both_neutral():
    res = merge_signals(
        symbol="EURUSD", timeframe="H1",
        voting_direction="NEUTRAL", voting_confidence=0.0,
        lstm_direction="HOLD", lstm_confidence=0.0,
        shadow_win_rate=0.5, shadow_trade_count=0
    )
    assert res.direction == "NEUTRAL"
    assert res.confidence == 0.0
    assert res.agreement is False
    print("test_both_neutral passed")

def test_zero_confidence():
    res = merge_signals(
        symbol="EURUSD", timeframe="H1",
        voting_direction="BUY", voting_confidence=0.0,
        lstm_direction="UP", lstm_confidence=0.0,
        shadow_win_rate=0.7, shadow_trade_count=50
    )
    assert res.direction == "NEUTRAL"
    assert res.confidence == 0.0
    print("test_zero_confidence passed")

def test_large_trade_count():
    res = merge_signals(
        symbol="EURUSD", timeframe="H1",
        voting_direction="BUY", voting_confidence=0.6,
        lstm_direction="UP", lstm_confidence=80,
        shadow_win_rate=0.6, shadow_trade_count=10000
    )
    assert res.direction == "BUY"
    assert res.lstm_weight_used > 0
    assert res.agreement is True
    print("test_large_trade_count passed")

def test_strong_conflict_veto():
    # Strong disagreement leading to veto (conflict_weight >= 0.45)
    res = merge_signals(
        symbol="EURUSD", timeframe="H1",
        voting_direction="BUY", voting_confidence=0.8,
        lstm_direction="DOWN", lstm_confidence=100,
        shadow_win_rate=0.9, shadow_trade_count=1000
    )
    assert res.direction == "NEUTRAL"
    assert res.confidence == 0.0
    assert res.audit_trail["veto"] is not None
    print("test_strong_conflict_veto passed")

if __name__ == "__main__":
    test_agreement_increases_confidence()
    test_disagreement_decreases_confidence()
    test_untrusted_lstm_has_low_weight()
    test_poor_lstm_history_suppressed()
    test_lstm_never_flips_direction_alone()
    test_both_neutral()
    test_zero_confidence()
    test_large_trade_count()
    test_strong_conflict_veto()
    print("All tests passed!")