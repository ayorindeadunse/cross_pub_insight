import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
@patch("utils.repo_utils.clone_if_remote")
@patch("agents.project_analyzer.ProjectAnalyzerAgent.analyze_project")
@patch("agents.trend_aggregator.run")
@patch("orchestrator.orchestrator.CrossPublicationInsightOrchestrator.run")
async def test_run_analysis_mocked(
    mock_orchestrator_run,
    mock_aggregate_trends,
    mock_analyze_project,
    mock_clone_if_remote,
    test_client
):
    # Mock dependencies
    mock_clone_if_remote.side_effect = lambda url: f"/local/path/to/{url.split('/')[-1]}"
    mock_analyze_project.return_value = "Mocked analysis result"
    mock_aggregate_trends.return_value = {"aggregated_trends": "Mocked trends"}
    mock_orchestrator_run.return_value = {
        "analysis_result": "Mocked analysis",
        "fact_check_result": "Mocked fact check",
        "aggregate_query_result": "Mocked aggregate query",
        "final_summary": "Mocked summary",
    }

    payload = {
        "primary_repo": "https://github.com/mockorg/mock-repo",
        "comparison_repos": ["https://github.com/mockorg/comp-repo1"],
        "user_query": "What is this project about?",
        "use_hitl": False,
    }

    response = await test_client.post("/run-analysis/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "processing"
