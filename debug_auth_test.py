#!/usr/bin/env python3

import requests

# Test authentication errors
BASE_URL = "https://tomi-learn.preview.emergentagent.com/api"

def test_auth_errors():
    endpoints = ["/conversations", "/business/setup", "/documents", "/ai/suggest-reply"]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            print(f"GET {endpoint}: Status {response.status_code}")
            if response.status_code == 401:
                print("✅ Correctly returned 401")
            else:
                print(f"❌ Expected 401, got {response.status_code}")
        except Exception as e:
            print(f"❌ Error for {endpoint}: {e}")

def test_invalid_resource():
    try:
        # First let's register and get a token
        register_data = {
            "name": "Test User",
            "email": f"test{hash('test')}@test.com",
            "phone": "+1555555555",
            "password": "TestPassword123!"
        }
        
        # Register user
        response = requests.post(f"{BASE_URL}/auth/register", json=register_data, timeout=10)
        if response.status_code == 200:
            token = response.json().get("token")
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test invalid conversation ID
            invalid_response = requests.get(f"{BASE_URL}/conversations/invalid_id", headers=headers, timeout=10)
            print(f"GET /conversations/invalid_id with auth: Status {invalid_response.status_code}")
            if invalid_response.status_code == 404:
                print("✅ Correctly returned 404 for invalid resource")
            else:
                print(f"❌ Expected 404, got {invalid_response.status_code}")
        else:
            print(f"❌ Failed to register user: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error in invalid resource test: {e}")

if __name__ == "__main__":
    print("Testing authentication errors...")
    test_auth_errors()
    print("\nTesting invalid resource errors...")
    test_invalid_resource()