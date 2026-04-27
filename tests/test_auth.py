import pytest

@pytest.mark.asyncio
async def test_cross_tenant_access_denied(async_client, auth_headers, test_user_id):
    # Token is for test_user_id
    headers = auth_headers(test_user_id)
    
    other_user_id = "some-other-user"
    
    # Try to access other user's data
    response = await async_client.get(
        f"/memory/{other_user_id}/context?relevantTo=test",
        headers=headers
    )
    
    assert response.status_code == 403
    data = response.json()
    assert data["error"] == "FORBIDDEN"
    assert "traceId" in data
