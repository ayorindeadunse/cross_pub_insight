import pytest
import time

@pytest.mark.asyncio
async def test_run_analysis_integration(test_client):
    payload = {
        "primary_repo": "https://github.com/rushter/MLAgorithms",
        "comparison_repos": ["https://github.com/GokuMohandas/Made-With-ML"],
        "user_query": "What trends in ML are emerging?",
        "use_hitl": False 
    }

    # Kick off the background job
    response = await test_client.post("/run-analysis/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    session_id = data["session_id"]

    # Poll the results
    for _ in range(30):  # Poll for up to 30 seconds
        poll_response = await test_client.get(f"/results/{session_id}")
        poll_data = poll_response.json()
        if poll_data["status"] == "completed":
            assert isinstance(poll_data["results"], list)
            break
        time.sleep(1)
    else:
        pytest.fail("Analysis did not complete in time")