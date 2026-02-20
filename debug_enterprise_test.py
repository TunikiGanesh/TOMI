#!/usr/bin/env python3
"""
Debug Enterprise Endpoints - Specific testing for issues found
"""

import requests
import json
import uuid

# Configuration
BASE_URL = "https://owner-command-center.preview.emergentagent.com/api"

def test_specific_endpoints():
    # Register a new user first
    test_email = f"debug.user.{uuid.uuid4().hex[:8]}@example.com"
    test_password = "DebugPassword123!"
    
    # Register
    register_data = {
        "name": "Debug User",
        "email": test_email,
        "phone": "+1-555-999-0000",
        "password": test_password
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    print(f"Registration Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"Registration failed: {response.text}")
        return
    
    auth_token = response.json()["token"]
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Setup business
    business_data = {
        "name": "Debug Business",
        "business_type": "Technology",
        "products_services": "Software development", 
        "working_hours": "9AM-5PM",
        "locations": ["Remote"],
        "team_size": "1-5 employees"
    }
    
    response = requests.post(f"{BASE_URL}/business/setup", json=business_data, headers=headers)
    print(f"Business Setup Status: {response.status_code}")
    
    # Complete onboarding
    response = requests.post(f"{BASE_URL}/onboarding/complete", headers=headers)
    print(f"Onboarding Status: {response.status_code}")
    
    # Now test the failing endpoints
    print("\n=== TESTING DATA EXPORT ===")
    export_data = {"format": "json"}
    response = requests.post(f"{BASE_URL}/data/export-all", json=export_data, headers=headers)
    print(f"Export Status: {response.status_code}")
    print(f"Export Response: {response.text[:500]}")
    
    print("\n=== TESTING AUTH ERROR HANDLING ===")
    # Test without auth token
    response = requests.get(f"{BASE_URL}/conversations")
    print(f"No Auth - Conversations Status: {response.status_code}")
    print(f"No Auth Response: {response.text}")
    
    response = requests.get(f"{BASE_URL}/business")
    print(f"No Auth - Business Status: {response.status_code}")
    print(f"No Auth Response: {response.text}")
    
    print("\n=== TESTING INVALID RESOURCE ===")
    # Test invalid conversation ID
    response = requests.get(f"{BASE_URL}/conversations/invalid_id", headers=headers)
    print(f"Invalid Conversation Status: {response.status_code}")
    print(f"Invalid Conversation Response: {response.text}")

if __name__ == "__main__":
    test_specific_endpoints()