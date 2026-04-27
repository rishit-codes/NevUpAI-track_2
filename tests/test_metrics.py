import pytest
from app.api.routes.sessions import session_state

@pytest.mark.asyncio
async def test_session_metrics(async_client, auth_headers, test_user_id):
    session_id = "test-session-123"
    headers = auth_headers(test_user_id)
    
    events = [
        {
            "tradeId": "1",
            "asset": "BTC",
            "assetClass": "crypto",
            "direction": "long",
            "entryPrice": 60000,
            "quantity": 1,
            "entryAt": "2025-01-01T10:00:00Z",
            "status": "closed",
            "outcome": "loss",
            "planAdherence": 2,
            "revengeFlag": True
        }
    ]
    
    response = await async_client.post(
        f"/sessions/{session_id}/events",
        json={"userId": test_user_id, "events": events},
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "metricsSnapshot" in data
    assert data["metricsSnapshot"]["revengeFlag"] is True
    assert data["metricsSnapshot"]["planAdherenceScore"] == 2.0
    assert "revenge_trading" in data["triggeredSignals"]
