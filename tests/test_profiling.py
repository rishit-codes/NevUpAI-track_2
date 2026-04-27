import pytest
from app.services.profiling.classifier import RuleBasedClassifier
from datetime import datetime, timezone

def test_revenge_trading():
    # Opened within 90 seconds of losing close, fearful state, revenge_flag=True
    trades = [
        {"tradeId": "1", "exitAt": "2025-01-01T10:00:00Z", "outcome": "loss"},
        {"tradeId": "2", "entryAt": "2025-01-01T10:01:00Z", "emotionalState": "fearful", "revengeFlag": True}
    ]
    classifier = RuleBasedClassifier("user1", [], trades)
    res = classifier._eval_revenge_trading()
    assert res is not None
    assert "2" in res["evidenceTrades"]
    assert res["pathology"] == "revenge_trading"

def test_overtrading():
    # >10 trades in 30 min window
    trades = []
    base_time = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    for i in range(12):
        entry_time = base_time.replace(minute=i).isoformat()
        trades.append({"tradeId": str(i), "entryAt": entry_time})
        
    classifier = RuleBasedClassifier("user1", [], trades)
    res = classifier._eval_overtrading()
    assert res is not None
    assert res["pathology"] == "overtrading"

def test_fomo_entries():
    trades = [
        {"tradeId": "1", "planAdherence": 2, "entryRationale": "trying to catch the move before it's too late"}
    ]
    classifier = RuleBasedClassifier("user1", [], trades)
    res = classifier._eval_fomo_entries()
    assert res is not None
    assert "1" in res["evidenceTrades"]

def test_plan_non_adherence():
    trades = [
        {"tradeId": "1", "planAdherence": 1, "entryRationale": "random impulse, not in plan"}
    ]
    classifier = RuleBasedClassifier("user1", [], trades)
    res = classifier._eval_plan_non_adherence()
    assert res is not None
    assert "1" in res["evidenceTrades"]

def test_premature_exit():
    trades = [
        {"tradeId": "1", "entryAt": "2025-01-01T10:00:00Z", "exitAt": "2025-01-01T11:00:00Z", "outcome": "win", "emotionalState": "calm"},
        {"tradeId": "2", "entryAt": "2025-01-01T12:00:00Z", "exitAt": "2025-01-01T12:05:00Z", "outcome": "win", "emotionalState": "fearful"},
        {"tradeId": "3", "entryAt": "2025-01-01T13:00:00Z", "exitAt": "2025-01-01T13:30:00Z", "outcome": "loss", "emotionalState": "calm"}
    ]
    classifier = RuleBasedClassifier("user1", [], trades)
    res = classifier._eval_premature_exit()
    assert res is not None
    assert "2" in res["evidenceTrades"]

def test_loss_running():
    trades = [
        {"tradeId": "1", "entryAt": "2025-01-01T10:00:00Z", "exitAt": "2025-01-01T10:10:00Z", "outcome": "win", "emotionalState": "calm"},
        {"tradeId": "2", "entryAt": "2025-01-01T12:00:00Z", "exitAt": "2025-01-01T13:00:00Z", "outcome": "loss", "emotionalState": "fearful", "entryRationale": "hoping"}
    ]
    classifier = RuleBasedClassifier("user1", [], trades)
    res = classifier._eval_loss_running()
    assert res is not None
    assert "2" in res["evidenceTrades"]

def test_session_tilt():
    trades = [
        {"tradeId": "1", "sessionId": "s1", "entryAt": "2025-01-01T10:00:00Z", "outcome": "loss"},
        {"tradeId": "2", "sessionId": "s1", "entryAt": "2025-01-01T10:10:00Z", "outcome": "loss"},
        {"tradeId": "3", "sessionId": "s1", "entryAt": "2025-01-01T10:20:00Z", "planAdherence": 1}
    ]
    classifier = RuleBasedClassifier("user1", [{"sessionId": "s1"}], trades)
    res = classifier._eval_session_tilt()
    assert res is not None
    assert "3" in res["evidenceTrades"]

def test_time_of_day_bias():
    trades = []
    # Create 5 bad trades at hour 14
    for i in range(5):
        trades.append({"tradeId": str(i), "entryAt": f"2025-01-01T14:1{i}:00Z", "pnl": -100})
    classifier = RuleBasedClassifier("user1", [], trades)
    res = classifier._eval_time_of_day_bias()
    assert res is not None
    assert res["pathology"] == "time_of_day_bias"

def test_position_sizing_inconsistency():
    trades = [
        {"tradeId": "1", "assetClass": "crypto", "quantity": 1},
        {"tradeId": "2", "assetClass": "crypto", "quantity": 10},
        {"tradeId": "3", "assetClass": "crypto", "quantity": 100},
        {"tradeId": "4", "assetClass": "crypto", "quantity": 0.1}
    ]
    classifier = RuleBasedClassifier("user1", [], trades)
    res = classifier._eval_position_sizing_inconsistency()
    assert res is not None
    assert res["pathology"] == "position_sizing_inconsistency"
