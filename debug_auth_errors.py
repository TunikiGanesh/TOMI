#!/usr/bin/env python3
"""
Debug authentication error handling
"""

import requests
import json

BASE_URL = "https://tomi-learn.preview.emergentagent.com/api"

def test_unauth_endpoints():
    """Test endpoints without authentication"""
    endpoints = ["/conversations", "/business/setup", "/documents", "/ai/suggest-reply"]
    
    for endpoint in endpoints:
        url = f"{BASE_URL}{endpoint}"
        response = requests.get(url, timeout=10)
        print(f"GET {endpoint}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        print("---")

def test_invalid_conversation():
    """Test invalid conversation ID"""
    # First register a user to get token
    register_data = {
        "name": "Test User",
        "email": "test@example.com",
        "phone": "+1555123456",
        "password": "password123"
    }
    
    register_response = requests.post(f"{BASE_URL}/auth/register", json=register_data, timeout=10)
    if register_response.status_code != 200:
        print("Failed to register user")
        return
    
    token = register_response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    invalid_id = "invalid_conversation_id"
    url = f"{BASE_URL}/conversations/{invalid_id}"
    response = requests.get(url, headers=headers, timeout=10)
    
    print(f"GET /conversations/{invalid_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")

if __name__ == "__main__":
    print("Testing unauthenticated endpoints:")
    test_unauth_endpoints()
    
    print("\nTesting invalid conversation ID:")
    test_invalid_conversation()