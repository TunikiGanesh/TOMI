"""
Iteration 4 Backend Tests: Auth Enhancements & Placeholder Fixes

This iteration tests:
1. POST /api/auth/register - creates new user successfully
2. POST /api/auth/login - works with email/password
3. POST /api/auth/login - auto-sets password for Google-only users (no password_hash)
4. POST /api/auth/register - merges Google-only account if same email
5. Database is clean (verified by 401 on login)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime
from pymongo import MongoClient

# Backend URL from env - no defaults
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tomi-chatbot-ai.preview.emergentagent.com').rstrip('/')

# MongoDB connection for direct DB operations
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

class TestHealthCheck:
    """Basic health check"""
    
    def test_health_endpoint(self):
        """API health check returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        print("✅ Health check passed")


class TestDatabaseIsClean:
    """Verify database was cleared"""
    
    def test_login_nonexistent_user(self):
        """Login should return 401 for non-existent user (database cleared)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "testfresh@tomi.com",
            "password": "Test123!"
        })
        assert response.status_code == 401
        data = response.json()
        assert data['detail'] == 'Invalid credentials'
        print("✅ Database clean - no existing users")


class TestUserRegistration:
    """Test POST /api/auth/register - new user creation"""
    
    def test_register_new_user_success(self):
        """Register creates a new user with token"""
        unique_email = f"TEST_new_{uuid.uuid4().hex[:8]}@tomi.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": unique_email,
            "phone": "+1234567890",
            "password": "Test123!"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert 'user' in data
        assert 'token' in data
        assert len(data['token']) > 0
        
        # Verify user data
        user = data['user']
        assert user['email'] == unique_email
        assert user['name'] == 'Test User'
        assert 'user_id' in user
        assert 'password_hash' not in user  # Should not expose password hash
        
        print(f"✅ Register new user success: {unique_email}")
        
        # Cleanup - delete test user
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        db.users.delete_one({"email": unique_email})
        client.close()
    
    def test_register_requires_name(self):
        """Register requires name field"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": "test@test.com",
            "phone": "+1234567890",
            "password": "Test123!"
        })
        assert response.status_code == 422  # Validation error
        print("✅ Register validates required name")
    
    def test_register_requires_email(self):
        """Register requires email field"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "phone": "+1234567890",
            "password": "Test123!"
        })
        assert response.status_code == 422  # Validation error
        print("✅ Register validates required email")
    
    def test_register_validates_email_format(self):
        """Register validates email format"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": "not-an-email",
            "phone": "+1234567890",
            "password": "Test123!"
        })
        assert response.status_code == 422  # Validation error
        print("✅ Register validates email format")


class TestUserLogin:
    """Test POST /api/auth/login"""
    
    @pytest.fixture(autouse=True)
    def setup_test_user(self):
        """Create test user before tests and cleanup after"""
        self.test_email = f"TEST_login_{uuid.uuid4().hex[:8]}@tomi.com"
        self.test_password = "TestPass123!"
        
        # Register user
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Login Test User",
            "email": self.test_email,
            "phone": "+1234567890",
            "password": self.test_password
        })
        assert response.status_code == 200
        
        yield
        
        # Cleanup
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        db.users.delete_one({"email": self.test_email})
        client.close()
    
    def test_login_success(self):
        """Login with valid credentials returns token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert 'user' in data
        assert 'token' in data
        assert len(data['token']) > 0
        
        # Verify user data - no password_hash exposed
        assert 'password_hash' not in data['user']
        
        print(f"✅ Login success for {self.test_email}")
    
    def test_login_wrong_password(self):
        """Login with wrong password returns 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.test_email,
            "password": "WrongPassword123!"
        })
        
        assert response.status_code == 401
        data = response.json()
        assert data['detail'] == 'Invalid credentials'
        print("✅ Login with wrong password returns 401")
    
    def test_login_nonexistent_user(self):
        """Login with non-existent email returns 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "AnyPassword123!"
        })
        
        assert response.status_code == 401
        data = response.json()
        assert data['detail'] == 'Invalid credentials'
        print("✅ Login non-existent user returns 401")


class TestGoogleOnlyUserAutoPassword:
    """
    Test POST /api/auth/login auto-sets password for Google-only users
    
    This is the KEY FIX: Previously, Google-only users (no password_hash) would crash
    with a 500 error when trying bcrypt.checkpw on None/empty string.
    
    Now, the login endpoint auto-sets the password for Google-verified users.
    """
    
    @pytest.fixture(autouse=True)
    def setup_google_only_user(self):
        """Create a Google-only user in DB (no password_hash)"""
        self.google_email = f"TEST_google_{uuid.uuid4().hex[:8]}@gmail.com"
        self.google_id = f"google_{uuid.uuid4().hex[:16]}"
        self.user_id = f"user_{uuid.uuid4().hex[:12]}"
        self.new_password = "NewPassword123!"
        
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Insert Google-only user (no password_hash)
        db.users.insert_one({
            "user_id": self.user_id,
            "name": "Google Only User",
            "email": self.google_email,
            "google_id": self.google_id,
            "created_at": datetime.utcnow(),
            "onboarding_completed": False
            # NOTE: No password_hash field!
        })
        
        client.close()
        
        yield
        
        # Cleanup
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        db.users.delete_one({"email": self.google_email})
        client.close()
    
    def test_google_only_user_login_auto_sets_password(self):
        """
        Login with Google-only user (no password_hash) should auto-set password
        instead of crashing with 500.
        """
        # First login - should auto-set password and succeed
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.google_email,
            "password": self.new_password
        })
        
        # Should succeed (200), not crash (500)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response
        assert 'user' in data
        assert 'token' in data
        assert data['user']['email'] == self.google_email
        assert 'password_hash' not in data['user']
        
        print(f"✅ Google-only user login auto-set password: {self.google_email}")
        
        # Verify password was persisted - login again with same password
        response2 = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.google_email,
            "password": self.new_password
        })
        
        assert response2.status_code == 200
        print("✅ Password persisted - second login works")
        
        # Verify wrong password now fails (password was set)
        response3 = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.google_email,
            "password": "WrongPassword!"
        })
        
        assert response3.status_code == 401
        print("✅ Wrong password now correctly fails")


class TestRegisterMergesGoogleAccount:
    """
    Test POST /api/auth/register merges Google-only account
    
    If a user registered via Google (no password_hash), then tries to register
    with email/password using the same email, it should merge the account
    (set password_hash) instead of failing.
    """
    
    @pytest.fixture(autouse=True)
    def setup_google_only_user(self):
        """Create a Google-only user in DB (no password_hash)"""
        self.google_email = f"TEST_merge_{uuid.uuid4().hex[:8]}@gmail.com"
        self.google_id = f"google_{uuid.uuid4().hex[:16]}"
        self.user_id = f"user_{uuid.uuid4().hex[:12]}"
        self.new_password = "MergedPassword123!"
        
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Insert Google-only user (no password_hash)
        db.users.insert_one({
            "user_id": self.user_id,
            "name": "Google Merge User",
            "email": self.google_email,
            "google_id": self.google_id,
            "created_at": datetime.utcnow(),
            "onboarding_completed": False
            # NOTE: No password_hash field!
        })
        
        client.close()
        
        yield
        
        # Cleanup
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        db.users.delete_one({"email": self.google_email})
        client.close()
    
    def test_register_merges_google_only_account(self):
        """
        Register with Google-only user's email should merge account
        (set password) instead of returning 'email already registered'.
        """
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Merged Name",
            "email": self.google_email,
            "phone": "+9999999999",
            "password": self.new_password
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response
        assert 'user' in data
        assert 'token' in data
        assert data['user']['email'] == self.google_email
        
        print(f"✅ Register merged Google-only account: {self.google_email}")
        
        # Verify can now login with password
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.google_email,
            "password": self.new_password
        })
        
        assert login_response.status_code == 200
        print("✅ Merged account can login with password")
    
    def test_register_existing_password_user_fails(self):
        """
        Register with email that already has a password should fail.
        """
        # First, set a password via login (uses auto-set feature)
        requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.google_email,
            "password": "ExistingPassword123!"
        })
        
        # Now try to register with same email - should fail
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Another Name",
            "email": self.google_email,
            "phone": "+8888888888",
            "password": "AnotherPassword123!"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert 'already registered' in data['detail'].lower()
        print("✅ Register with existing password user fails correctly")


class TestAuthCallbackDeepLink:
    """Test /api/auth-callback endpoint for mobile deep linking"""
    
    def test_auth_callback_returns_html(self):
        """Auth callback returns HTML redirect page"""
        response = requests.get(f"{BASE_URL}/api/auth-callback")
        assert response.status_code == 200
        assert 'text/html' in response.headers.get('content-type', '')
        print("✅ Auth callback returns HTML")
    
    def test_auth_callback_contains_query_param_deep_link(self):
        """Auth callback uses ?session_id= query param for Android compatibility"""
        response = requests.get(f"{BASE_URL}/api/auth-callback")
        html = response.text
        
        # Should use query param (?session_id=) not hash (#session_id=) for Android
        assert "tomi://auth-callback?session_id=" in html
        print("✅ Auth callback uses query param for deep link")
    
    def test_auth_callback_handles_both_param_styles(self):
        """Auth callback JS handles both hash and query params"""
        response = requests.get(f"{BASE_URL}/api/auth-callback")
        html = response.text
        
        # Should extract from hash (Emergent Auth default)
        assert "hash.match(/session_id=([^&]+)/)" in html
        # Should also try query params as fallback
        assert "URLSearchParams" in html
        print("✅ Auth callback handles both hash and query params")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
