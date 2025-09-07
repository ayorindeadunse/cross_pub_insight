import pytest
import time
from httpx import AsyncClient
from api.server import api

@pytest.mark.asyncio
async def test_run_analysis_integration():
    payload = {
        "primary_repo": "https://github.com/rushter/MLAgorithms",
        "comparison_repos": ["https://github.com/GokuMohandas/Made-With-ML"],
        "user_query": "What trends in ML are emerging?",
        "use_hitl": False 
    }

    async with AsyncClient(api=api, base_url="http://test") as ac:
        response = await ac.post("/run-analysis/",json=payload)
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]

        # Poll the results (simulate waiting)
        for _ in range(30): # try up to 30 seconds
            result_resp = await ac.get(f"/results/{session_id}")
            result_data = result_resp.json()
            if result_data["status"] == "completed":
                assert "results" in result_data
                assert isinstance(result_data["results"], list)
                return
            time.sleep(1)
        
        pytest.fail("Analysis did not complete in time")