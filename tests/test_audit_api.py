import pytest
import uuid

@pytest.mark.asyncio
async def test_audit_endpoint(async_client, auth_headers, test_user_id):
    headers = auth_headers(test_user_id)
    
    # We use a completely fake session
    fake_session_1 = str(uuid.uuid4())
    fake_session_2 = str(uuid.uuid4())
    
    response = await async_client.post(
        "/audit/",
        json={
            "userId": test_user_id,
            "referencedSessions": [fake_session_1, fake_session_2]
        },
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["sessionId"] == fake_session_1
    assert data[0]["found"] is False
    assert data[1]["found"] is False
