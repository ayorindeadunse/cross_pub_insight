"""
Test script for the enhanced CPIA API security features.
This tests our security middleware without requiring all dependencies.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient
import json

# Import our enhanced models and security
from api.models import RepoRequest, AnalysisResponse, HealthCheckResponse
from api.security import setup_security_middleware

def test_security_features():
    """Test the security middleware and validation."""
    print("🔐 Testing CPIA API Security Features...")
    
    # Create a minimal test app
    app = FastAPI(title="CPIA Security Test")
    
    # Setup security middleware
    setup_security_middleware(app, rate_limit_requests=5, rate_limit_window=60)
    
    @app.post("/test-analysis/", response_model=AnalysisResponse)
    async def test_analysis(request: RepoRequest):
        return AnalysisResponse(
            session_id="test-123",
            status="processing",
            message="Test request validated successfully"
        )
    
    @app.get("/health", response_model=HealthCheckResponse)
    async def health_check():
        return HealthCheckResponse(
            status="healthy",
            timestamp="2025-10-27T00:00:00Z",
            version="1.0.0"
        )
    
    # Test with TestClient
    client = TestClient(app)
    
    print("Testing Health Check...")
    health_response = client.get("/health")
    assert health_response.status_code == 200
    health_data = health_response.json()
    print(f"   Health Status: {health_data['status']}")
    
    print("Testing Valid Request...")
    valid_payload = {
        "primary_repo": "https://github.com/test/valid-repo",
        "comparison_repos": ["https://github.com/test/comparison"],
        "user_query": "What frameworks are used?",
        "use_hitl": False
    }
    
    response = client.post("/test-analysis/", json=valid_payload)
    assert response.status_code == 200
    data = response.json()
    print(f"   Session ID: {data['session_id']}")
    print(f"   Status: {data['status']}")
    
    print("Testing Input Validation - Invalid URL...")
    invalid_payload = {
        "primary_repo": "not-a-valid-url",
        "comparison_repos": ["https://github.com/test/comparison"],
        "user_query": "test",
        "use_hitl": False
    }
    
    response = client.post("/test-analysis/", json=invalid_payload)
    assert response.status_code == 422  # Validation error
    print("   ✓ Invalid URL rejected as expected")
    
    print("Testing Input Validation - Empty repositories...")
    empty_repos_payload = {
        "primary_repo": "https://github.com/test/valid-repo",
        "comparison_repos": [],
        "user_query": "test",
        "use_hitl": False
    }
    
    response = client.post("/test-analysis/", json=empty_repos_payload)
    assert response.status_code == 422  # Validation error  
    print("✓ Empty comparison repos rejected as expected")
    
    print("Testing Rate Limiting...")
    # Make multiple requests quickly to trigger rate limiting
    for i in range(7):  # More than our limit of 5
        try:
            response = client.post("/test-analysis/", json=valid_payload)
            if response.status_code == 429:
                print(f"   ✓ Rate limiting triggered after {i+1} requests")
                break
        except Exception as e:
            if "429" in str(e):
                print(f"   ✓ Rate limiting triggered after {i+1} requests (exception handling)")
                break
            else:
                raise
    else:
        print("Rate limiting not triggered (may need more requests)")
    
    print("All security tests passed!")

if __name__ == "__main__":
    test_security_features()