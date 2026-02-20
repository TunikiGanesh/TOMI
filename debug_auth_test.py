#!/usr/bin/env python3
"""
Debug Auth Issues - Check why auth error tests are failing
"""

import requests
import json
import uuid

# Configuration
BASE_URL = "https://tomi-owner-mind.preview.emergentagent.com/api"

def debug_auth_tests():
    print("=== DEBUGGING AUTH ERROR HANDLING ===")
    
    # Test without any authentication header
    print("\n1. Testing /conversations without auth:")
    try:
        response = requests.get(f"{BASE_URL}/conversations", timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n2. Testing /business without auth:")
    try:
        response = requests.get(f"{BASE_URL}/business", timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n3. Testing /documents without auth:")
    try:
        response = requests.get(f"{BASE_URL}/documents", timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== DEBUGGING INVALID RESOURCE HANDLING ===")
    
    # Register user first to get auth token for invalid resource test
    test_email = f"debug2.user.{uuid.uuid4().hex[:8]}@example.com"
    register_data = {
        "name": "Debug User 2",
        "email": test_email,
        "phone": "+1-555-999-0001",
        "password": "DebugPassword123!"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    if response.status_code == 200:
        auth_token = response.json()["token"]
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Setup business
        business_data = {
            "name": "Debug Business 2",
            "business_type": "Technology",
            "products_services": "Software development", 
            "working_hours": "9AM-5PM",
            "locations": ["Remote"],
            "team_size": "1-5 employees"
        }
        requests.post(f"{BASE_URL}/business/setup", json=business_data, headers=headers)
        
        print("\n4. Testing invalid conversation ID:")
        try:
            response = requests.get(f"{BASE_URL}/conversations/invalid_conversation_id", headers=headers, timeout=30)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Failed to register user for invalid resource test")

if __name__ == "__main__":
    debug_auth_tests()