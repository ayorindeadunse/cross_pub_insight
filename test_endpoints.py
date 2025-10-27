"""
Test script to verify all CPIA endpoints are working correctly.
"""
import asyncio
import json
import requests
import time
from typing import Dict, Any

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(endpoint: str, method: str = "GET", data: Dict[Any, Any] = None) -> Dict[str, Any]:
    """Test a single endpoint and return results"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        start_time = time.time()
        
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        
        duration_ms = (time.time() - start_time) * 1000
        
        return {
            "endpoint": endpoint,
            "method": method,
            "status_code": response.status_code,
            "success": 200 <= response.status_code < 300,
            "response_time_ms": round(duration_ms, 2),
            "response_size": len(response.content),
            "content_type": response.headers.get("content-type", ""),
            "response_preview": str(response.text)[:200] + "..." if len(response.text) > 200 else response.text
        }
    
    except requests.exceptions.ConnectionError:
        return {
            "endpoint": endpoint,
            "method": method,
            "status_code": None,
            "success": False,
            "error": "Connection Error - Server not running",
            "response_time_ms": 0
        }
    except requests.exceptions.Timeout:
        return {
            "endpoint": endpoint,
            "method": method,
            "status_code": None,
            "success": False,
            "error": "Timeout Error",
            "response_time_ms": 10000
        }
    except Exception as e:
        return {
            "endpoint": endpoint,
            "method": method,
            "status_code": None,
            "success": False,
            "error": str(e),
            "response_time_ms": 0
        }

def main():
    """Test all CPIA endpoints"""
    print("🚀 Testing CPIA Server Endpoints")
    print("=" * 50)
    
    # Test endpoints
    endpoints = [
        # Basic health and info
        {"endpoint": "/", "method": "GET"},
        {"endpoint": "/health", "method": "GET"},
        {"endpoint": "/monitoring/health", "method": "GET"},
        {"endpoint": "/monitoring/metrics", "method": "GET"},
        {"endpoint": "/monitoring/status", "method": "GET"},
        
        # API documentation
        {"endpoint": "/docs", "method": "GET"},
        {"endpoint": "/redoc", "method": "GET"},
        
        # Analysis endpoint (with mock data)
        {
            "endpoint": "/run-analysis/",
            "method": "POST",
            "data": {
                "primary_repo": "https://github.com/microsoft/vscode",
                "comparison_repos": [],
                "user_query": "What technologies does this project use?",
                "use_hitl": False
            }
        }
    ]
    
    results = []
    successful_tests = 0
    total_tests = len(endpoints)
    
    for test_config in endpoints:
        print(f"\nTesting {test_config['method']} {test_config['endpoint']}...")
        
        result = test_endpoint(
            test_config["endpoint"],
            test_config["method"],
            test_config.get("data")
        )
        
        results.append(result)
        
        if result["success"]:
            successful_tests += 1
            print(f"✅ SUCCESS - {result['status_code']} ({result['response_time_ms']}ms)")
        else:
            print(f"❌ FAILED - {result.get('error', result.get('status_code', 'Unknown error'))}")
        
        if "response_preview" in result:
            print(f"   Response: {result['response_preview']}")
    
    # Summary
    print("\n" + "=" * 50)
    print("🏁 Test Summary")
    print("=" * 50)
    print(f"Total Endpoints Tested: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {total_tests - successful_tests}")
    print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")
    
    # Detailed results
    print("\n📊 Detailed Results:")
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['method']} {result['endpoint']} - {result.get('status_code', 'ERROR')}")
    
    # Performance summary
    successful_results = [r for r in results if r["success"]]
    if successful_results:
        avg_response_time = sum(r["response_time_ms"] for r in successful_results) / len(successful_results)
        print(f"\n⚡ Average Response Time: {avg_response_time:.2f}ms")
    
    return successful_tests == total_tests

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)