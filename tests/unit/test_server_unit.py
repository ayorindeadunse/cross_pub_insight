import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient
from api.server import api 

@pytest.mark.asyncio
@patch("api.server.clone_if_remote")
@patch("api.server.ProjectAnalyzerAgent.analyze_project")
@patch("api.server.CrossPublicationInsightOrchestrator.run")
@patch("api.server.aggregate_trends")

async def test_run_analysis_mocked(
    mock_aggregate_trends,
    mock_orchestrator_run,
    mock_analyze_project,
    mock_clone_if_remote
):
    mock_clone_if_remote.side_effect = lambda url: f"/local/path/to/{url.split('/')[-1]}"
    mock_analyze_project.return_value = "Mocked analysis result"
    mock_aggregate_trends.return_value = {"aggregated_trends": "Mocked trends"}
    mock_orchestrator_run.return_value = {
        "analysis_result": "Mocked analysis",
        "fact_check_result": "Mocked fact check",
        "aggregate_query_result": "Mocked aggregate query",
        "final_summary": "Mocked summary"
    }

    payload = {
        "primary_repo": "https://github.com/mockorg/mock-repo",
        "comparison_repos": ["https://github.com/mockorg/comp-repo1"],
        "user_query":"What is this project about?",
        "use_hitl": False
    }

    async with AsyncClient(api=api, base_url="http://test") as ac:
        response = await ac.post("/run_analysis", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "processing"
    