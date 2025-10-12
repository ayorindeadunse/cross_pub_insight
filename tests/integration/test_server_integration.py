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
    async with test_client as ac:
        response = await ac.post("/run-analysis/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        session_id = data["session_id"]

        # Poll the results
        for _ in range(30):  # Poll for up to 30 seconds
            result_response = await ac.get(f"/results/{session_id}")
            result_data = result_response.json()
            if result_data["status"] == "completed":
                assert "results" in result_data
                assert isinstance(result_data["results"], list)
                return
            time.sleep(1)
        
        pytest.fail("Analysis did not complete in time")
       

   