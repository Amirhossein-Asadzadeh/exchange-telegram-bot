from posbot.watcher import detect_crossing

def test_loss_to_profit():
    assert detect_crossing(-10, +10, threshold=5) == "LOSS_TO_PROFIT"

def test_profit_to_loss():
    assert detect_crossing(+10, -10, threshold=5) == "PROFIT_TO_LOSS"

def test_no_crossing_inside_zone():
    assert detect_crossing(-3, -6, threshold=5) is None
