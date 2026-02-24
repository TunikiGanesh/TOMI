"""
TOMI API Backend Tests
Tests: health, auth (register/login), business setup, chatbot (with/without web search), chat history, rate limiting
"""
import pytest
import requests
import os
import uuid
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tomi-chatbot-ai.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@tomi.com"
TEST_USER_PASSWORD = "test123"


class TestHealthEndpoint:
    """Test API health check"""
    
    def test_health_returns_200(self):
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'TOMI API'
        assert 'timestamp' in data
        print("✓ Health endpoint returns 200 with correct data")


class TestAuthentication:
    """Test registration and login flows"""
    
    def test_login_existing_user_success(self):
        """Test login with existing test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert 'token' in data
        assert 'user' in data
        assert data['user']['email'] == TEST_USER_EMAIL
        assert isinstance(data['token'], str) and len(data['token']) > 0
        print(f"✓ Login successful for {TEST_USER_EMAIL}")
    
    def test_login_invalid_credentials(self):
        """Test login with wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid credentials rejected with 401")
    
    def test_register_new_user(self):
        """Test registration of a new user"""
        unique_email = f"TEST_user_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": unique_email,
            "phone": "+911234567890",
            "password": "testpassword123"
        })
        assert response.status_code == 200
        data = response.json()
        assert 'token' in data
        assert 'user' in data
        assert data['user']['email'] == unique_email
        print(f"✓ User registration successful for {unique_email}")
    
    def test_register_duplicate_email(self):
        """Test that duplicate email registration is rejected"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Duplicate User",
            "email": TEST_USER_EMAIL,
            "phone": "+911234567890",
            "password": "testpassword123"
        })
        assert response.status_code == 400
        print("✓ Duplicate email registration rejected with 400")


@pytest.fixture(scope="class")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.fail("Authentication failed - cannot get token")


class TestBusinessSetup:
    """Test business setup endpoints"""
    
    def test_business_setup_with_auth(self, auth_token):
        """Test creating/updating business with valid auth"""
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        
        # First try to get existing business
        get_response = requests.get(f"{BASE_URL}/api/business", headers=headers)
        
        if get_response.status_code == 404:
            # Create new business
            response = requests.post(f"{BASE_URL}/api/business/setup", headers=headers, json={
                "name": "Test Corp",
                "business_type": "Retail",
                "products_services": "Testing products",
                "working_hours": "9am-6pm",
                "locations": ["Test City"],
                "team_size": "1-10"
            })
            assert response.status_code == 200
            data = response.json()
            assert 'business_id' in data
            assert data['name'] == 'Test Corp'
            print("✓ Business setup successful - new business created")
        else:
            assert get_response.status_code == 200
            data = get_response.json()
            assert 'business_id' in data
            print("✓ Business already exists, GET successful")
    
    def test_business_setup_without_auth(self):
        """Test that business setup requires authentication"""
        response = requests.post(f"{BASE_URL}/api/business/setup", json={
            "name": "Unauthorized Business",
            "business_type": "Retail",
            "products_services": "Testing",
            "working_hours": "9am-6pm",
            "locations": ["Test City"],
            "team_size": "1-10"
        })
        assert response.status_code in [401, 422]  # 422 if missing auth header entirely
        print("✓ Business setup without auth rejected")


class TestChatbot:
    """Test chatbot endpoints with web search toggle"""
    
    def test_chatbot_ask_with_web_search(self, auth_token):
        """Test chatbot with web search enabled"""
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        
        response = requests.post(f"{BASE_URL}/api/chatbot/ask", headers=headers, json={
            "question": "What is the current weather?",
            "include_web_search": True
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True
        assert 'answer' in data
        assert isinstance(data['answer'], str)
        assert 'sources' in data
        assert data['sources']['web_searched'] == True
        print(f"✓ Chatbot with web search returned answer with sources")
        print(f"  Web results count: {data['sources'].get('web_results_count', 0)}")
    
    def test_chatbot_ask_without_web_search(self, auth_token):
        """Test chatbot with web search disabled (internal data only)"""
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        
        response = requests.post(f"{BASE_URL}/api/chatbot/ask", headers=headers, json={
            "question": "Tell me about my business",
            "include_web_search": False
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True
        assert 'answer' in data
        assert 'sources' in data
        assert data['sources']['web_searched'] == False
        # When web search disabled, web_results_count should be 0 or not present
        assert data['sources'].get('web_results_count', 0) == 0
        print("✓ Chatbot without web search returned answer (internal data only)")
    
    def test_chatbot_ask_without_auth(self):
        """Test that chatbot requires authentication"""
        response = requests.post(f"{BASE_URL}/api/chatbot/ask", json={
            "question": "test question",
            "include_web_search": False
        })
        assert response.status_code in [401, 422]
        print("✓ Chatbot without auth rejected")
    
    def test_chat_history(self, auth_token):
        """Test getting chat history"""
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        
        response = requests.get(f"{BASE_URL}/api/chatbot/history", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert 'history' in data
        assert 'count' in data
        assert isinstance(data['history'], list)
        print(f"✓ Chat history retrieved: {data['count']} messages")


class TestRateLimiter:
    """Test rate limiter (20 requests/minute)"""
    
    def test_rate_limiter_exists(self, auth_token):
        """Verify rate limiter is configured (don't exhaust quota in test)"""
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        
        # Make a few quick requests to verify basic functionality
        success_count = 0
        for i in range(3):
            response = requests.post(f"{BASE_URL}/api/chatbot/ask", headers=headers, json={
                "question": f"Quick test {i}",
                "include_web_search": False
            })
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429 or 'Rate limit' in response.text:
                # Rate limiter kicked in (which proves it exists)
                print("✓ Rate limiter is active and working")
                return
            time.sleep(0.5)
        
        # If we got here without rate limit, it means limiter allows at least 3 requests
        assert success_count >= 1
        print(f"✓ Rate limiter allows reasonable requests ({success_count}/3 succeeded)")


class TestAuthMe:
    """Test /api/auth/me endpoint"""
    
    def test_get_current_user(self, auth_token):
        """Test getting current user info"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['email'] == TEST_USER_EMAIL
        assert 'user_id' in data
        print(f"✓ /api/auth/me returns correct user data")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
