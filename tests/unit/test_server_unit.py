import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
@patch("api.server.clone_if_remote")
@patch("api.server.ProjectAnalyzerAgent")
@patch("api.server.aggregate_trends")
@patch("api.server.CrossPublicationInsightOrchestrator")
async def test_run_analysis_mocked(
    mock_orchestrator_class,
    mock_aggregate_trends,
    mock_analyzer_class,
    mock_clone_if_remote,
    test_client
):
    # Mock the clone_if_remote function to return local paths
    mock_clone_if_remote.side_effect = lambda url: f"/local/path/to/{url.split('/')[-1]}"
    
    # Mock the ProjectAnalyzerAgent class and its instance
    mock_analyzer_instance = MagicMock()
    mock_analyzer_instance.analyze_project.return_value = "Mocked analysis result"
    mock_analyzer_class.return_value = mock_analyzer_instance
    
    # Mock the trend aggregator
    mock_aggregate_trends.return_value = {"aggregated_trends": "Mocked trends"}
    
    # Mock the orchestrator class and its instance
    mock_orchestrator_instance = MagicMock()
    mock_orchestrator_instance.run.return_value = {
        "analysis_result": "Mocked analysis",
        "fact_check_result": "Mocked fact check",
        "aggregate_query_result": "Mocked aggregate query",
        "final_summary": "Mocked summary",
    }
    mock_orchestrator_class.return_value = mock_orchestrator_instance

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
    assert "status" in data
    assert data["status"] == "processing"

    # Verify the mocks were called correctly
    # clone_if_remote should be called twice: once for primary repo, once for comparison repo
    assert mock_clone_if_remote.call_count == 2
    
    # ProjectAnalyzerAgent should be instantiated for comparison repo analysis
    mock_analyzer_class.assert_called_with(llm_type="local")
    mock_analyzer_instance.analyze_project.assert_called_once()
    
    # trend aggregator should be called
    mock_aggregate_trends.assert_called_once()
    
    # orchestrator should be instantiated and run
    mock_orchestrator_class.assert_called_once()
    mock_orchestrator_instance.run.assert_called_once()


@pytest.mark.asyncio
async def test_get_results_endpoint(test_client):
    """Test the results endpoint"""
    # Test with non-existent session
    response = await test_client.get("/results/non-existent-session")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_found"


@pytest.mark.asyncio
async def test_run_analysis_validation(test_client):
    """Test request validation for run_analysis endpoint"""
    # Test with missing required fields
    payload = {
        "comparison_repos": ["https://github.com/mockorg/comp-repo1"],
        "user_query": "What is this project about?",
    }
    
    response = await test_client.post("/run-analysis/", json=payload)
    assert response.status_code == 422  # Validation error
  
