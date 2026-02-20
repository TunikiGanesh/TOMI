#!/usr/bin/env python3
"""
Debug test for specific failing endpoints
"""

import requests
import json
import os
import uuid

BASE_URL = "https://tomi-owner-mind.preview.emergentagent.com/api"
TEST_EMAIL = f"debug.test.{uuid.uuid4().hex[:8]}@example.com"
TEST_PASSWORD = "SecureTestPassword123!"

def make_request(method, endpoint, data=None, files=None, headers=None, token=None):
    """Make authenticated HTTP request"""
    url = f"{BASE_URL}{endpoint}"
    req_headers = headers or {}
    
    if token:
        req_headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=req_headers, timeout=30)
        elif method == "POST":
            if files:
                response = requests.post(url, files=files, data=data, headers=req_headers, timeout=30)
            else:
                req_headers["Content-Type"] = "application/json"
                response = requests.post(url, json=data, headers=req_headers, timeout=30)
        elif method == "PUT":
            req_headers["Content-Type"] = "application/json"
            response = requests.put(url, json=data, headers=req_headers, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, headers=req_headers, timeout=30)
        
        print(f"{method} {endpoint}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        print("---")
        return response
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def debug_failing_endpoints():
    print("🔍 Debugging failing endpoints...")
    
    # Setup user and business
    register_data = {
        "name": "Debug User",
        "email": TEST_EMAIL,
        "phone": "+1555-999-1234",
        "password": TEST_PASSWORD
    }
    
    response = make_request("POST", "/auth/register", register_data)
    if not response or response.status_code != 200:
        print("❌ Failed to register")
        return
    
    token = response.json()["token"]
    
    # Setup business
    business_data = {
        "name": "Debug Business",
        "business_type": "Testing",
        "products_services": "Debug services",
        "working_hours": "24/7",
        "locations": ["Debug Location"],
        "team_size": "1"
    }
    
    response = make_request("POST", "/business/setup", business_data, token=token)
    if not response or response.status_code != 200:
        print("❌ Failed to setup business")
        return
    
    business_id = response.json()["business_id"]
    
    # Test 1: Update business
    print("\n🔧 Testing PUT /api/business")
    update_data = {
        "name": "Updated Debug Business",
        "business_type": "Updated Testing",
        "products_services": "Updated debug services",
        "working_hours": "Updated 24/7",
        "locations": ["Updated Debug Location"],
        "team_size": "Updated 1"
    }
    
    response = make_request("PUT", "/business", update_data, token=token)
    
    # Test 2: Upload and delete document
    print("\n📄 Testing document upload and delete")
    
    test_content = "Debug document content for testing"
    temp_file = "/tmp/debug_doc.txt"
    with open(temp_file, "w") as f:
        f.write(test_content)
    
    try:
        with open(temp_file, "rb") as f:
            files = {"file": ("debug.txt", f, "text/plain")}
            data = {"category": "test"}
            
            response = make_request("POST", "/documents/upload", data=data, files=files, token=token)
        
        if response and response.status_code == 200:
            doc_id = response.json().get("document_id")
            if doc_id:
                print(f"\n🗑️ Testing DELETE /api/documents/{doc_id}")
                response = make_request("DELETE", f"/documents/{doc_id}", token=token)
    
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    
    # Test 3: AI Insights
    print("\n🤖 Testing GET /api/ai/insights")
    response = make_request("GET", "/ai/insights", token=token)

if __name__ == "__main__":
    debug_failing_endpoints()