import pytest

@pytest.mark.asyncio
async def test_coaching_sse_stream(async_client, auth_headers, test_user_id):
    session_id = "stream-test-session"
    headers = auth_headers(test_user_id)
    
    async with async_client.stream("GET", f"/sessions/{session_id}/coaching", headers=headers) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        
        events = []
        async for line in response.aiter_lines():
            if line:
                events.append(line)
                
        # We expect at least event: token and event: done
        assert any(e.startswith("event: token") for e in events)
        assert any(e.startswith("event: done") for e in events)
        
        # Verify JSON data
        data_lines = [e for e in events if e.startswith("data:")]
        import json
        last_data = json.loads(data_lines[-1].replace("data: ", ""))
        assert "fullMessage" in last_data
