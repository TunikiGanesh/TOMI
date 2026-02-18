#!/usr/bin/env python3
"""
TOMI Backend Phase 3 AI Integration Testing Script
Tests all AI-related endpoints with authentication and business context
"""
import asyncio
import httpx
import json
import uuid
import io
from typing import Dict, Any, Optional

# Test configuration
BACKEND_URL = "https://tomi-learn.preview.emergentagent.com/api"
TEST_USER_DATA = {
    "name": "Sarah Johnson",
    "email": f"sarah.johnson+test{uuid.uuid4().hex[:6]}@businessowner.com",
    "phone": "+1-555-0123",
    "password": "SecureTestPass123!"
}

TEST_BUSINESS_DATA = {
    "name": "Sarah's Digital Marketing Agency", 
    "business_type": "Marketing & Advertising",
    "products_services": "Digital marketing services including social media management, SEO, content creation, and paid advertising for small to medium businesses",
    "working_hours": "Monday-Friday 9:00 AM - 6:00 PM EST, Saturday 10:00 AM - 2:00 PM EST",
    "locations": ["New York, NY", "Remote Services Available"],
    "team_size": "5-10 employees"
}

class TOMITester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.auth_token = None
        self.user_id = None
        self.business_id = None
        self.conversation_id = None
        self.document_id = None
        self.test_results = {}
        
    async def cleanup(self):
        """Cleanup HTTP client"""
        await self.client.aclose()
        
    def log_result(self, test_name: str, success: bool, details: str, data: Any = None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        self.test_results[test_name] = {
            "success": success,
            "details": details,
            "data": data
        }
        
    async def test_user_registration(self):
        """Test user registration"""
        try:
            response = await self.client.post(f"{BACKEND_URL}/auth/register", json=TEST_USER_DATA)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("token")
                self.user_id = data.get("user", {}).get("user_id")
                
                if self.auth_token and self.user_id:
                    self.log_result("User Registration", True, f"User created successfully with ID: {self.user_id}")
                    return True
                else:
                    self.log_result("User Registration", False, f"Missing token or user_id in response: {data}")
                    return False
            else:
                error_detail = response.text
                self.log_result("User Registration", False, f"Status {response.status_code}: {error_detail}")
                return False
                
        except Exception as e:
            self.log_result("User Registration", False, f"Exception occurred: {str(e)}")
            return False
            
    async def test_business_setup(self):
        """Test business setup"""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = await self.client.post(f"{BACKEND_URL}/business/setup", 
                                              json=TEST_BUSINESS_DATA, 
                                              headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.business_id = data.get("business_id")
                
                if self.business_id:
                    self.log_result("Business Setup", True, f"Business created successfully with ID: {self.business_id}")
                    return True
                else:
                    self.log_result("Business Setup", False, f"Missing business_id in response: {data}")
                    return False
            else:
                error_detail = response.text
                self.log_result("Business Setup", False, f"Status {response.status_code}: {error_detail}")
                return False
                
        except Exception as e:
            self.log_result("Business Setup", False, f"Exception occurred: {str(e)}")
            return False
            
    async def test_document_upload(self):
        """Test document upload for business context"""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Create test business document content
            business_info_content = """
SERVICE PRICING GUIDE - Sarah's Digital Marketing Agency

Our Core Services:

1. SOCIAL MEDIA MANAGEMENT
   - Basic Package: $800/month (2 platforms, 12 posts/month)
   - Standard Package: $1,200/month (3 platforms, 20 posts/month)
   - Premium Package: $1,800/month (4 platforms, 30 posts/month, stories)

2. SEO SERVICES
   - Local SEO Setup: $1,500 one-time
   - Monthly SEO Management: $900/month
   - E-commerce SEO: $1,200/month

3. CONTENT CREATION
   - Blog Writing: $150 per 1,000-word article
   - Video Content: $300 per short-form video
   - Graphic Design: $75 per post design

4. PAID ADVERTISING
   - Google Ads Management: 15% of ad spend (min $500/month)
   - Facebook/Instagram Ads: 12% of ad spend (min $400/month)
   - Ad Creative Development: $200 per campaign

BUSINESS POLICIES:
- Payment terms: Net 30 days
- Contract minimum: 3 months for monthly services
- Setup fees apply for new clients
- 24-hour response time for client communications
- Monthly reporting included in all packages

CONTACT INFORMATION:
Phone: (555) 123-4567
Email: hello@sarahsdigitalagency.com
Office Hours: Mon-Fri 9AM-6PM EST, Sat 10AM-2PM EST
Address: 123 Broadway, Suite 456, New York, NY 10001
"""
            
            # Create file-like object
            file_content = io.BytesIO(business_info_content.encode('utf-8'))
            
            files = {
                'file': ('business_info.txt', file_content, 'text/plain')
            }
            
            response = await self.client.post(f"{BACKEND_URL}/documents/upload", 
                                              files=files,
                                              headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.document_id = data.get("document_id")
                extracted_text = data.get("extracted_text", "")
                
                if self.document_id and extracted_text:
                    self.log_result("Document Upload", True, f"Document uploaded successfully with ID: {self.document_id}, extracted {len(extracted_text)} chars")
                    return True
                else:
                    self.log_result("Document Upload", False, f"Missing document_id or extracted_text: {data}")
                    return False
            else:
                error_detail = response.text
                self.log_result("Document Upload", False, f"Status {response.status_code}: {error_detail}")
                return False
                
        except Exception as e:
            self.log_result("Document Upload", False, f"Exception occurred: {str(e)}")
            return False

    async def test_conversation_management(self):
        """Test conversation CRUD operations"""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Test 1: Create conversation
            conversation_data = {
                "channel": "email",
                "contact_name": "Mike Thompson", 
                "contact_info": "mike.thompson@techdemo.com",
                "initial_message": "Hi! I'm interested in your social media management services. What packages do you offer and what are your rates?"
            }
            
            response = await self.client.post(f"{BACKEND_URL}/conversations", 
                                              json=conversation_data,
                                              headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.conversation_id = data.get("conversation_id")
                
                if self.conversation_id:
                    self.log_result("Create Conversation", True, f"Conversation created with ID: {self.conversation_id}")
                else:
                    self.log_result("Create Conversation", False, f"Missing conversation_id: {data}")
                    return False
            else:
                self.log_result("Create Conversation", False, f"Status {response.status_code}: {response.text}")
                return False
                
            # Test 2: List conversations
            response = await self.client.get(f"{BACKEND_URL}/conversations", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                conversations = data.get("conversations", [])
                
                if len(conversations) > 0:
                    self.log_result("List Conversations", True, f"Retrieved {len(conversations)} conversations")
                else:
                    self.log_result("List Conversations", False, "No conversations found")
                    return False
            else:
                self.log_result("List Conversations", False, f"Status {response.status_code}: {response.text}")
                return False
                
            # Test 3: Add message to conversation
            message_data = {
                "content": "Thank you for your inquiry! I'd be happy to discuss our social media packages with you.",
                "sender": "owner"
            }
            
            response = await self.client.post(f"{BACKEND_URL}/conversations/{self.conversation_id}/messages",
                                              json=message_data,
                                              headers=headers)
            
            if response.status_code == 200:
                self.log_result("Add Message", True, "Message added successfully")
            else:
                self.log_result("Add Message", False, f"Status {response.status_code}: {response.text}")
                return False
                
            # Test 4: Get conversation with messages
            response = await self.client.get(f"{BACKEND_URL}/conversations/{self.conversation_id}", 
                                             headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", [])
                
                if len(messages) >= 2:  # Initial message + added message
                    self.log_result("Get Conversation with Messages", True, f"Retrieved conversation with {len(messages)} messages")
                    return True
                else:
                    self.log_result("Get Conversation with Messages", False, f"Expected 2+ messages, got {len(messages)}")
                    return False
            else:
                self.log_result("Get Conversation with Messages", False, f"Status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Conversation Management", False, f"Exception occurred: {str(e)}")
            return False

    async def test_ai_reply_suggestion(self):
        """Test AI reply suggestion endpoint"""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Test AI reply with business context
            request_data = {
                "message": "What are your business hours and do you work on weekends?",
                "conversation_id": self.conversation_id
            }
            
            response = await self.client.post(f"{BACKEND_URL}/ai/suggest-reply",
                                              json=request_data,
                                              headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                suggested_reply = data.get("suggested_reply")
                model_used = data.get("model_used")
                context_used = data.get("context_used")
                
                if suggested_reply and model_used:
                    # Check if the reply contains business context (working hours)
                    has_business_context = any(term in suggested_reply.lower() for term in 
                                               ["monday", "friday", "9", "6", "saturday", "hours", "est"])
                    
                    if has_business_context:
                        self.log_result("AI Reply Suggestion", True, 
                                        f"AI generated context-aware reply using {model_used}. Context used: {context_used}")
                        print(f"   Sample reply: {suggested_reply[:100]}...")
                        return True
                    else:
                        self.log_result("AI Reply Suggestion", False, 
                                        f"Reply doesn't contain business context: {suggested_reply}")
                        return False
                else:
                    self.log_result("AI Reply Suggestion", False, f"Missing suggested_reply or model_used: {data}")
                    return False
            else:
                error_detail = response.text
                self.log_result("AI Reply Suggestion", False, f"Status {response.status_code}: {error_detail}")
                return False
                
        except Exception as e:
            self.log_result("AI Reply Suggestion", False, f"Exception occurred: {str(e)}")
            return False

    async def test_message_analysis(self):
        """Test message analysis endpoint"""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            request_data = {
                "message": "I need help ASAP! My Facebook ads aren't working and I'm losing money. Can you fix this today??"
            }
            
            response = await self.client.post(f"{BACKEND_URL}/ai/analyze-message",
                                              json=request_data,
                                              headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for required analysis fields
                required_fields = ["intent", "sentiment", "urgency"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    intent = data.get("intent")
                    sentiment = data.get("sentiment") 
                    urgency = data.get("urgency")
                    
                    # Validate analysis makes sense for the urgent message
                    expected_high_urgency = urgency in ["high", "urgent"]
                    expected_negative_sentiment = sentiment in ["negative", "urgent", "frustrated"]
                    
                    if expected_high_urgency and expected_negative_sentiment:
                        self.log_result("Message Analysis", True, 
                                        f"Analysis correct - Intent: {intent}, Sentiment: {sentiment}, Urgency: {urgency}")
                        return True
                    else:
                        self.log_result("Message Analysis", False, 
                                        f"Analysis doesn't match message tone - Intent: {intent}, Sentiment: {sentiment}, Urgency: {urgency}")
                        return False
                else:
                    self.log_result("Message Analysis", False, f"Missing required fields: {missing_fields}")
                    return False
            else:
                error_detail = response.text
                self.log_result("Message Analysis", False, f"Status {response.status_code}: {error_detail}")
                return False
                
        except Exception as e:
            self.log_result("Message Analysis", False, f"Exception occurred: {str(e)}")
            return False

    async def test_ai_insights(self):
        """Test AI insights endpoint"""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            response = await self.client.get(f"{BACKEND_URL}/ai/insights", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                insight = data.get("insight")
                generated_at = data.get("generated_at")
                
                if insight and generated_at:
                    # Check if insight contains business-relevant content
                    has_business_relevance = any(term in insight.lower() for term in 
                                                 ["conversation", "business", "customer", "marketing", "activity"])
                    
                    if has_business_relevance:
                        self.log_result("AI Insights", True, f"Generated business insight at {generated_at}")
                        print(f"   Sample insight: {insight[:150]}...")
                        return True
                    else:
                        self.log_result("AI Insights", False, f"Insight doesn't seem business-relevant: {insight}")
                        return False
                else:
                    self.log_result("AI Insights", False, f"Missing insight or generated_at: {data}")
                    return False
            else:
                error_detail = response.text
                self.log_result("AI Insights", False, f"Status {response.status_code}: {error_detail}")
                return False
                
        except Exception as e:
            self.log_result("AI Insights", False, f"Exception occurred: {str(e)}")
            return False

    async def test_error_handling(self):
        """Test error handling for AI endpoints"""
        try:
            # Test 1: Unauthenticated request
            response = await self.client.post(f"{BACKEND_URL}/ai/suggest-reply", 
                                              json={"message": "test"})
            
            if response.status_code == 401:
                self.log_result("Error Handling - Unauthenticated", True, "Correctly returned 401 for unauthenticated request")
            else:
                self.log_result("Error Handling - Unauthenticated", False, f"Expected 401, got {response.status_code}")
                
            # Test 2: Invalid conversation ID
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = await self.client.get(f"{BACKEND_URL}/conversations/invalid_id", headers=headers)
            
            if response.status_code == 404:
                self.log_result("Error Handling - Invalid Conversation", True, "Correctly returned 404 for invalid conversation ID")
                return True
            else:
                self.log_result("Error Handling - Invalid Conversation", False, f"Expected 404, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Error Handling", False, f"Exception occurred: {str(e)}")
            return False

    async def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting TOMI Backend Phase 3 AI Integration Tests")
        print("=" * 60)
        
        # Authentication setup tests
        if not await self.test_user_registration():
            print("❌ Cannot proceed without user registration")
            return False
            
        if not await self.test_business_setup():
            print("❌ Cannot proceed without business setup")  
            return False
            
        if not await self.test_document_upload():
            print("❌ Cannot proceed without document upload for context")
            return False
            
        # Core AI feature tests  
        print("\n🤖 Testing AI Integration Features:")
        print("-" * 40)
        
        ai_tests = [
            self.test_conversation_management(),
            self.test_ai_reply_suggestion(), 
            self.test_message_analysis(),
            self.test_ai_insights(),
            self.test_error_handling()
        ]
        
        results = await asyncio.gather(*ai_tests, return_exceptions=True)
        
        # Summary
        print("\n📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for test_name, result in self.test_results.items():
                if not result["success"]:
                    print(f"   • {test_name}: {result['details']}")
                    
        return failed_tests == 0

async def main():
    tester = TOMITester()
    try:
        success = await tester.run_all_tests()
        return success
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)