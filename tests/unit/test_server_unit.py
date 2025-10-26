import pytest
from unittest.mock import patch, MagicMock
import json


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
@patch("api.server.clone_if_remote")
@patch("api.server.ProjectAnalyzerAgent")
@patch("api.server.aggregate_trends")
@patch("api.server.CrossPublicationInsightOrchestrator")
async def test_run_analysis_with_multiple_comparison_repos(
    mock_orchestrator_class,
    mock_aggregate_trends,
    mock_analyzer_class,
    mock_clone_if_remote,
    test_client
):
    """Test analysis with multiple comparison repositories"""
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
        "comparison_repos": [
            "https://github.com/mockorg/comp-repo1",
            "https://github.com/mockorg/comp-repo2",
            "https://github.com/mockorg/comp-repo3"
        ],
        "user_query": "What is this project about?",
        "use_hitl": True,
    }

    response = await test_client.post("/run-analysis/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "status" in data
    assert data["status"] == "processing"

    # Verify the mocks were called correctly
    # clone_if_remote should be called 4 times: once for primary repo, three for comparison repos
    assert mock_clone_if_remote.call_count == 4
    
    # ProjectAnalyzerAgent should be instantiated 3 times for each comparison repo
    assert mock_analyzer_class.call_count == 3
    assert mock_analyzer_instance.analyze_project.call_count == 3
    
    # trend aggregator should be called 3 times for each comparison repo
    assert mock_aggregate_trends.call_count == 3
    
    # orchestrator should run 3 times for each comparison
    assert mock_orchestrator_instance.run.call_count == 3


@pytest.mark.asyncio
async def test_get_results_endpoint(test_client):
    """Test the results endpoint"""
    # Test with non-existent session
    response = await test_client.get("/results/non-existent-session")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_found"


@pytest.mark.asyncio
async def test_get_results_with_existing_session(test_client):
    """Test getting results for an existing session"""
    from api.server import session_store
    
    # Manually add a session to the store
    session_id = "test-session-123"
    session_store[session_id] = {
        "status": "completed",
        "results": [
            {
                "comparison_repo": "/path/to/repo",
                "analysis_result": "Test analysis",
                "fact_check_result": "Test fact check",
                "aggregate_query_result": "Test query",
                "final_summary": "Test summary"
            }
        ]
    }
    
    response = await test_client.get(f"/results/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["analysis_result"] == "Test analysis"
    
    # Clean up
    del session_store[session_id]


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


@pytest.mark.asyncio
@patch("api.server.clone_if_remote")
async def test_run_analysis_with_empty_comparison_repos(mock_clone_if_remote, test_client):
    """Test analysis with empty comparison repos list"""
    mock_clone_if_remote.side_effect = lambda url: f"/local/path/to/{url.split('/')[-1]}"
    
    payload = {
        "primary_repo": "https://github.com/mockorg/mock-repo",
        "comparison_repos": [],
        "user_query": "What is this project about?",
        "use_hitl": False,
    }
    
    response = await test_client.post("/run-analysis/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "processing"


@pytest.mark.asyncio
@patch("api.server.CrossPublicationInsightOrchestrator")
@patch("api.server.aggregate_trends")
@patch("api.server.ProjectAnalyzerAgent")
@patch("api.server.clone_if_remote")
async def test_run_analysis_with_optional_fields(mock_clone_if_remote, mock_project_analyzer, mock_aggregate_trends, mock_orchestrator, test_client):
    """Test analysis with optional fields omitted"""
    mock_clone_if_remote.side_effect = lambda url: f"/local/path/to/{url.split('/')[-1]}"
    
    # Mock ProjectAnalyzerAgent
    mock_analyzer_instance = MagicMock()
    mock_analyzer_instance.analyze_repository.return_value = "Mock analysis result"
    mock_project_analyzer.return_value = mock_analyzer_instance
    
    # Mock aggregate_trends
    mock_aggregate_trends.return_value = {"aggregated_trends": ["trend1", "trend2"]}
    
    # Mock CrossPublicationInsightOrchestrator
    mock_orchestrator_instance = MagicMock()
    mock_orchestrator_instance.run_orchestration.return_value = {
        "primary_analysis": "Primary mock analysis",
        "comparison_analyses": ["Comparison mock analysis"],
        "fact_check_results": ["Fact check result"],
        "aggregate_query_results": ["Query result"],
        "final_summary": "Final mock summary"
    }
    mock_orchestrator.return_value = mock_orchestrator_instance
    
    payload = {
        "primary_repo": "https://github.com/mockorg/mock-repo",
        "comparison_repos": ["https://github.com/mockorg/comp-repo1"],
    }
    
    response = await test_client.post("/run-analysis/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "processing"


@pytest.mark.asyncio
async def test_run_analysis_with_invalid_json(test_client):
    """Test analysis with invalid JSON"""
    response = await test_client.post(
        "/run-analysis/", 
        content="invalid json",
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@patch("api.server.CrossPublicationInsightOrchestrator")
@patch("api.server.aggregate_trends")
@patch("api.server.ProjectAnalyzerAgent")
@patch("api.server.clone_if_remote")
async def test_session_id_uniqueness(mock_clone_if_remote, mock_project_analyzer, mock_aggregate_trends, mock_orchestrator, test_client):
    """Test that each analysis gets a unique session ID"""
    mock_clone_if_remote.side_effect = lambda url: f"/local/path/to/{url.split('/')[-1]}"
    
    # Mock ProjectAnalyzerAgent
    mock_analyzer_instance = MagicMock()
    mock_analyzer_instance.analyze_repository.return_value = "Mock analysis result"
    mock_project_analyzer.return_value = mock_analyzer_instance
    
    # Mock aggregate_trends
    mock_aggregate_trends.return_value = {"aggregated_trends": ["trend1", "trend2"]}
    
    # Mock CrossPublicationInsightOrchestrator
    mock_orchestrator_instance = MagicMock()
    mock_orchestrator_instance.run_orchestration.return_value = {
        "primary_analysis": "Primary mock analysis",
        "comparison_analyses": ["Comparison mock analysis"],
        "fact_check_results": ["Fact check result"],
        "aggregate_query_results": ["Query result"],
        "final_summary": "Final mock summary"
    }
    mock_orchestrator.return_value = mock_orchestrator_instance
    
    payload = {
        "primary_repo": "https://github.com/mockorg/mock-repo",
        "comparison_repos": ["https://github.com/mockorg/comp-repo1"],
        "user_query": "What is this project about?",
        "use_hitl": False,
    }

    # Make two identical requests
    response1 = await test_client.post("/run-analysis/", json=payload)
    response2 = await test_client.post("/run-analysis/", json=payload)
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    data1 = response1.json()
    data2 = response2.json()
    
    # Session IDs should be different
    assert data1["session_id"] != data2["session_id"]
  
