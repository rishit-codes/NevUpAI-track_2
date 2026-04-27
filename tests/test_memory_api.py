import pytest
import uuid

@pytest.mark.asyncio
async def test_memory_upsert_and_get(async_client, auth_headers, test_user_id):
    session_id = "4f39c2ea-8687-41f7-85a0-1fafd3e976df"
    headers = auth_headers(test_user_id)
    
    payload = {
        "summary": "This is a test summary",
        "metrics": {"planAdherenceScore": 4.5},
        "tags": ["revenge_trading"]
    }
    
    # 1. Upsert (PUT)
    response = await async_client.put(
        f"/memory/{test_user_id}/sessions/{session_id}",
        json=payload,
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == payload["summary"]
    
    # 2. GET Round-trip
    response_get = await async_client.get(
        f"/memory/{test_user_id}/sessions/{session_id}",
        headers=headers
    )
    assert response_get.status_code == 200
    assert response_get.json()["summary"] == payload["summary"]
    
    # 3. GET Context
    response_ctx = await async_client.get(
        f"/memory/{test_user_id}/context?relevantTo=revenge_trading",
        headers=headers
    )
    assert response_ctx.status_code == 200
    ctx_data = response_ctx.json()
    assert len(ctx_data["sessions"]) >= 1
    assert ctx_data["sessions"][0]["sessionId"] == session_id
