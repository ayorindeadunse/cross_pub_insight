#!/usr/bin/env python3
"""
Quick test script to verify the API response format
"""
import asyncio
import uvicorn
import threading
import time
import requests
import json
from api.server import app

def start_server():
    """Start the server in a separate thread"""
    uvicorn.run(app, host='127.0.0.1', port=8000, log_level='info')

def test_api():
    """Test the API endpoints"""
    session_id = "743818ec-79b6-4341-a623-5f919b8e3003"
    
    # Test health endpoint
    try:
        response = requests.get('http://127.0.0.1:8000/health', timeout=5)
        print(f"Health check - Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Health response: {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
    
    # Test get_results endpoint
    try:
        response = requests.get(f'http://127.0.0.1:8000/get_results/{session_id}', timeout=5)
        print(f"\nGet results - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response keys: {list(data.keys())}")
            
            # Check if our fix worked - should have analysis_result field
            if 'analysis_result' in data:
                print("✅ SUCCESS: 'analysis_result' field found in response!")
                print(f"Analysis result type: {type(data['analysis_result'])}")
                if isinstance(data['analysis_result'], list):
                    print(f"Analysis result length: {len(data['analysis_result'])}")
            else:
                print("❌ PROBLEM: 'analysis_result' field missing from response")
                print(f"Available fields: {list(data.keys())}")
        else:
            print(f"Error response: {response.text}")
            
    except Exception as e:
        print(f"Get results failed: {e}")

if __name__ == "__main__":
    print("Starting server...")
    
    # Start server in daemon thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    print("Waiting for server startup...")
    time.sleep(5)
    
    print("Testing API...")
    test_api()
    
    print("\nDone!")