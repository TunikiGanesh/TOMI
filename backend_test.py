#!/usr/bin/env python3
"""
Comprehensive TOMI Backend Testing - All Phases (1-7)
Tests complete user flow from registration to automation
"""

import requests
import json
import os
import time
from pathlib import Path
import uuid

# Configuration
BASE_URL = "https://owner-command-center.preview.emergentagent.com/api"
TEST_EMAIL = f"test.owner.{uuid.uuid4().hex[:8]}@example.com"
TEST_PASSWORD = "SecureTestPassword123!"
TEST_NAME = "Sarah Johnson"
TEST_PHONE = "+1555-123-4567"

class TOMIBackendTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.user_data = None
        self.business_id = None
        self.conversation_id = None
        self.document_id = None
        self.automation_id = None
        self.customer_id = None
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "failures": []
        }
    
    def log_test(self, test_name, success, details=""):
        """Log test result"""
        self.results["total_tests"] += 1
        if success:
            self.results["passed"] += 1
            print(f"✅ {test_name}")
        else:
            self.results["failed"] += 1
            self.results["failures"].append({"test": test_name, "details": details})
            print(f"❌ {test_name}: {details}")
    
    def make_request(self, method, endpoint, data=None, files=None, headers=None):
        """Make authenticated HTTP request"""
        url = f"{self.base_url}{endpoint}"
        req_headers = headers or {}
        
        if self.auth_token:
            req_headers["Authorization"] = f"Bearer {self.auth_token}"
        
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
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return response
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed for {endpoint}: {str(e)}")
            return None

    # ============ PHASE 1: AUTHENTICATION & ONBOARDING ============
    
    def test_user_registration(self):
        """Test POST /api/auth/register"""
        data = {
            "name": TEST_NAME,
            "email": TEST_EMAIL,
            "phone": TEST_PHONE,
            "password": TEST_PASSWORD
        }
        
        response = self.make_request("POST", "/auth/register", data)
        
        if response and response.status_code == 200:
            result = response.json()
            if "user" in result and "token" in result:
                self.auth_token = result["token"]
                self.user_data = result["user"]
                self.log_test("User Registration", True)
                return True
            else:
                self.log_test("User Registration", False, "Missing user or token in response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("User Registration", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    def test_user_login(self):
        """Test POST /api/auth/login"""
        data = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        
        response = self.make_request("POST", "/auth/login", data)
        
        if response and response.status_code == 200:
            result = response.json()
            if "user" in result and "token" in result:
                self.auth_token = result["token"]  # Update token
                self.log_test("User Login", True)
                return True
            else:
                self.log_test("User Login", False, "Missing user or token in response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("User Login", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    def test_get_current_user(self):
        """Test GET /api/auth/me"""
        response = self.make_request("GET", "/auth/me")
        
        if response and response.status_code == 200:
            user_data = response.json()
            if "user_id" in user_data and "email" in user_data:
                self.log_test("Get Current User", True)
                return True
            else:
                self.log_test("Get Current User", False, "Missing required user fields")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Get Current User", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    def test_business_setup(self):
        """Test POST /api/business/setup"""
        data = {
            "name": "Sarah's Consulting Services",
            "business_type": "Professional Services",
            "products_services": "Business strategy consulting and coaching for small businesses",
            "working_hours": "Monday-Friday 9AM-5PM EST",
            "locations": ["Remote", "New York, NY"],
            "team_size": "1-5 employees"
        }
        
        response = self.make_request("POST", "/business/setup", data)
        
        if response and response.status_code == 200:
            business_data = response.json()
            if "business_id" in business_data:
                self.business_id = business_data["business_id"]
                self.log_test("Business Setup", True)
                return True
            else:
                self.log_test("Business Setup", False, "Missing business_id in response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Business Setup", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    def test_communication_preferences(self):
        """Test POST /api/business/communication-preferences"""
        data = {
            "channels": ["email", "sms", "whatsapp"]
        }
        
        response = self.make_request("POST", "/business/communication-preferences", data)
        
        if response and response.status_code == 200:
            result = response.json()
            if "message" in result:
                self.log_test("Communication Preferences", True)
                return True
            else:
                self.log_test("Communication Preferences", False, "Missing success message")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Communication Preferences", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    def test_onboarding_completion(self):
        """Test POST /api/onboarding/complete - Should work WITHOUT documents"""
        response = self.make_request("POST", "/onboarding/complete")
        
        if response and response.status_code == 200:
            result = response.json()
            if "message" in result and "documents_uploaded" in result:
                # Should work even if documents_uploaded is 0
                self.log_test("Onboarding Completion (Without Documents)", True)
                return True
            else:
                self.log_test("Onboarding Completion", False, "Missing expected fields in response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Onboarding Completion", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    # ============ PHASE 2: DOCUMENT MANAGEMENT ============
    
    def test_document_upload(self):
        """Test POST /api/documents/upload with OCR"""
        # Create a simple text file for testing
        test_content = """BUSINESS INFORMATION
        
Sarah's Consulting Services
Professional Strategy Consulting

Services Offered:
- Business Strategy Development
- Market Analysis 
- Growth Planning
- Team Development

Contact: sarah@consulting.com
Phone: +1-555-123-4567
        """
        
        # Create temporary file
        temp_file = "/tmp/test_business_doc.txt"
        with open(temp_file, "w") as f:
            f.write(test_content)
        
        try:
            with open(temp_file, "rb") as f:
                files = {"file": ("business_info.txt", f, "text/plain")}
                data = {"category": "business_info"}
                
                response = self.make_request("POST", "/documents/upload", data=data, files=files)
            
            if response and response.status_code == 200:
                result = response.json()
                if "document_id" in result and "extracted_text" in result and result.get("success"):
                    self.document_id = result["document_id"]
                    # Verify OCR extraction worked
                    if "Sarah's Consulting" in result["extracted_text"]:
                        self.log_test("Document Upload with OCR", True)
                        return True
                    else:
                        self.log_test("Document Upload", False, "OCR extraction failed to extract expected text")
                else:
                    self.log_test("Document Upload", False, "Missing required fields or extraction failed")
            else:
                error_detail = response.json().get("detail", "Unknown error") if response else "No response"
                self.log_test("Document Upload", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        
        return False
    
    def test_get_documents(self):
        """Test GET /api/documents"""
        response = self.make_request("GET", "/documents")
        
        if response and response.status_code == 200:
            result = response.json()
            if "documents" in result and "count" in result:
                # Should have at least the document we uploaded
                if result["count"] > 0:
                    self.log_test("Get Documents", True)
                    return True
                else:
                    self.log_test("Get Documents", False, "No documents found after upload")
            else:
                self.log_test("Get Documents", False, "Missing expected fields in response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Get Documents", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    # ============ PHASE 3: CONVERSATIONS & MESSAGES ============
    
    def test_create_conversation(self):
        """Test POST /api/conversations"""
        data = {
            "channel": "email",
            "contact_name": "Emma Martinez",
            "contact_info": "emma.martinez@client.com",
            "initial_message": "Hi Sarah, I'm interested in your business strategy consulting services. Do you have availability for a consultation next week? I'm looking to expand my retail business and need guidance on market positioning."
        }
        
        response = self.make_request("POST", "/conversations", data)
        
        if response and response.status_code == 200:
            conversation = response.json()
            if "conversation_id" in conversation:
                self.conversation_id = conversation["conversation_id"]
                self.log_test("Create Conversation", True)
                return True
            else:
                self.log_test("Create Conversation", False, "Missing conversation_id in response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Create Conversation", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    def test_get_conversations(self):
        """Test GET /api/conversations"""
        response = self.make_request("GET", "/conversations")
        
        if response and response.status_code == 200:
            result = response.json()
            if "conversations" in result and "count" in result:
                if result["count"] > 0:
                    self.log_test("Get Conversations", True)
                    return True
                else:
                    self.log_test("Get Conversations", False, "No conversations found after creation")
            else:
                self.log_test("Get Conversations", False, "Missing expected fields in response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Get Conversations", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    def test_add_message(self):
        """Test POST /api/conversations/{id}/messages"""
        if not self.conversation_id:
            self.log_test("Add Message", False, "No conversation_id available")
            return False
        
        data = {
            "content": "Thank you for your interest! I'd be happy to help with your retail business expansion. I have availability Tuesday and Thursday next week for a consultation. My consultation fee is $150/hour and we can start with a 2-hour strategic assessment. Would either of those days work for you?",
            "sender": "owner"
        }
        
        response = self.make_request("POST", f"/conversations/{self.conversation_id}/messages", data)
        
        if response and response.status_code == 200:
            message = response.json()
            if "message_id" in message and "content" in message:
                self.log_test("Add Message", True)
                return True
            else:
                self.log_test("Add Message", False, "Missing required fields in message response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Add Message", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    def test_get_conversation_with_messages(self):
        """Test GET /api/conversations/{id}"""
        if not self.conversation_id:
            self.log_test("Get Conversation with Messages", False, "No conversation_id available")
            return False
        
        response = self.make_request("GET", f"/conversations/{self.conversation_id}")
        
        if response and response.status_code == 200:
            conversation = response.json()
            if "messages" in conversation and "conversation_id" in conversation:
                if len(conversation["messages"]) > 0:
                    self.log_test("Get Conversation with Messages", True)
                    return True
                else:
                    self.log_test("Get Conversation with Messages", False, "No messages found in conversation")
            else:
                self.log_test("Get Conversation with Messages", False, "Missing expected fields in conversation")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Get Conversation with Messages", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    # ============ PHASE 4: AI SERVICES ============
    
    def test_ai_suggest_reply(self):
        """Test POST /api/ai/suggest-reply"""
        data = {
            "message": "What are your pricing options for ongoing business coaching? I'm particularly interested in monthly retainer arrangements.",
            "conversation_id": self.conversation_id
        }
        
        response = self.make_request("POST", "/ai/suggest-reply", data)
        
        if response and response.status_code == 200:
            result = response.json()
            if "suggested_reply" in result and "model_used" in result:
                # Verify AI generated a meaningful response
                reply = result["suggested_reply"]
                if len(reply) > 50 and ("pricing" in reply.lower() or "retainer" in reply.lower() or "coaching" in reply.lower()):
                    self.log_test("AI Reply Suggestion", True)
                    return True
                else:
                    self.log_test("AI Reply Suggestion", False, "AI response seems too short or irrelevant")
            else:
                self.log_test("AI Reply Suggestion", False, "Missing required fields in AI response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("AI Reply Suggestion", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    def test_ai_analyze_message(self):
        """Test POST /api/ai/analyze-message"""
        data = {
            "message": "I'm extremely frustrated! I've been waiting 3 days for someone to respond to my urgent request about my project deadline. This is completely unacceptable service!"
        }
        
        response = self.make_request("POST", "/ai/analyze-message", data)
        
        if response and response.status_code == 200:
            analysis = response.json()
            if "intent" in analysis and "sentiment" in analysis and "urgency" in analysis:
                # Verify analysis is reasonable
                if (analysis["sentiment"] == "negative" and 
                    analysis["urgency"] in ["high", "medium"] and
                    analysis["intent"] in ["complaint", "inquiry"]):
                    self.log_test("AI Message Analysis", True)
                    return True
                else:
                    self.log_test("AI Message Analysis", False, f"Analysis seems incorrect: {analysis}")
            else:
                self.log_test("AI Message Analysis", False, "Missing required analysis fields")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("AI Message Analysis", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    # ============ PHASE 5: DECISION LEARNING ============
    
    def test_record_decision(self):
        """Test POST /api/decisions/record"""
        data = {
            "action_type": "discount_approval",
            "context": {
                "customer_type": "returning_client",
                "request_amount": "10%",
                "order_value": 500,
                "relationship_length": "6 months"
            },
            "decision": "approved",
            "automation_eligible": True
        }
        
        response = self.make_request("POST", "/decisions/record", data)
        
        if response and response.status_code == 200:
            result = response.json()
            if "recorded" in result and "decision_id" in result:
                self.log_test("Record Decision", True)
                return True
            else:
                self.log_test("Record Decision", False, "Missing required fields in decision response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Record Decision", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    def test_get_decision_patterns(self):
        """Test GET /api/decisions"""
        response = self.make_request("GET", "/decisions")
        
        if response and response.status_code == 200:
            result = response.json()
            if "decisions" in result and "patterns" in result:
                self.log_test("Get Decision Patterns", True)
                return True
            else:
                self.log_test("Get Decision Patterns", False, "Missing expected fields in patterns response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Get Decision Patterns", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    # ============ PHASE 6: AUTOMATION MANAGEMENT ============
    
    def test_create_automation(self):
        """Test POST /api/automations"""
        data = {
            "action_type": "discount_approval",
            "conditions": {
                "customer_type": "returning_client",
                "max_discount": "10%",
                "min_order_value": 300
            },
            "action": "auto_approve_discount",
            "enabled": False,
            "requires_approval": True
        }
        
        response = self.make_request("POST", "/automations", data)
        
        if response and response.status_code == 200:
            automation = response.json()
            if "automation_id" in automation:
                self.automation_id = automation["automation_id"]
                self.log_test("Create Automation", True)
                return True
            else:
                self.log_test("Create Automation", False, "Missing automation_id in response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Create Automation", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    def test_get_automations(self):
        """Test GET /api/automations"""
        response = self.make_request("GET", "/automations")
        
        if response and response.status_code == 200:
            result = response.json()
            if "automations" in result and "count" in result:
                self.log_test("Get Automations", True)
                return True
            else:
                self.log_test("Get Automations", False, "Missing expected fields in automations response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Get Automations", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    def test_toggle_automation(self):
        """Test PUT /api/automations/{id}/toggle"""
        if not self.automation_id:
            self.log_test("Toggle Automation", False, "No automation_id available")
            return False
        
        # Test enabling automation
        response = self.make_request("PUT", f"/automations/{self.automation_id}/toggle?enabled=true")
        
        if response and response.status_code == 200:
            result = response.json()
            if "automation_id" in result and "enabled" in result:
                if result["enabled"] == True:
                    self.log_test("Toggle Automation", True)
                    return True
                else:
                    self.log_test("Toggle Automation", False, "Automation not enabled as expected")
            else:
                self.log_test("Toggle Automation", False, "Missing expected fields in toggle response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Toggle Automation", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    # ============ PHASE 7: CHANNEL SIMULATOR ============
    
    def test_channel_simulator_email(self):
        """Test POST /api/channels/simulate/email"""
        response = self.make_request("POST", "/channels/simulate/email")
        
        if response and response.status_code == 200:
            result = response.json()
            if "simulated" in result and "conversation" in result and "message" in result:
                if result["simulated"] == True and "conversation_id" in result["conversation"]:
                    self.log_test("Channel Simulator Email", True)
                    return True
                else:
                    self.log_test("Channel Simulator Email", False, "Simulation not marked as successful or missing conversation")
            else:
                self.log_test("Channel Simulator Email", False, "Missing expected fields in simulation response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Channel Simulator Email", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    def test_channel_simulator_sms(self):
        """Test POST /api/channels/simulate/sms"""
        response = self.make_request("POST", "/channels/simulate/sms")
        
        if response and response.status_code == 200:
            result = response.json()
            if "simulated" in result and "conversation" in result and "message" in result:
                if result["simulated"] == True and "conversation_id" in result["conversation"]:
                    self.log_test("Channel Simulator SMS", True)
                    return True
                else:
                    self.log_test("Channel Simulator SMS", False, "Simulation not marked as successful or missing conversation")
            else:
                self.log_test("Channel Simulator SMS", False, "Missing expected fields in simulation response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Channel Simulator SMS", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    # ============ NEW ENTERPRISE ENDPOINTS ============
    
    def test_chatbot_ask(self):
        """Test POST /api/chatbot/ask"""
        data = {
            "question": "What are the main services offered by my business and their pricing structure?",
            "include_web_search": False
        }
        
        response = self.make_request("POST", "/chatbot/ask", data)
        
        if response and response.status_code == 200:
            result = response.json()
            if "answer" in result and "success" in result:
                if result["success"] and len(result["answer"]) > 50:
                    self.log_test("Chatbot Ask", True)
                    return True
                else:
                    self.log_test("Chatbot Ask", False, "Empty or too short answer from chatbot")
            else:
                self.log_test("Chatbot Ask", False, "Missing required fields in chatbot response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Chatbot Ask", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    def test_create_customer(self):
        """Test POST /api/customers"""
        data = {
            "name": "Emily Chen",
            "email": "emily.chen@example.com", 
            "phone": "+1-555-789-0123",
            "address": "456 Business Ave, Austin, TX 78701",
            "notes": "Interested in monthly business coaching services",
            "tags": ["potential_client", "monthly_retainer"]
        }
        
        response = self.make_request("POST", "/customers", data)
        
        if response and response.status_code == 200:
            result = response.json()
            if "success" in result and "customer_id" in result:
                if result["success"]:
                    self.customer_id = result["customer_id"]
                    self.log_test("Create Customer", True)
                    return True
                else:
                    self.log_test("Create Customer", False, "Success field is false")
            else:
                self.log_test("Create Customer", False, "Missing required fields in customer response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Create Customer", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    def test_get_customers(self):
        """Test GET /api/customers"""
        response = self.make_request("GET", "/customers")
        
        if response and response.status_code == 200:
            result = response.json()
            if "customers" in result and "count" in result:
                # Should have at least the customer we created
                if result["count"] > 0:
                    self.log_test("Get Customers", True)
                    return True
                else:
                    self.log_test("Get Customers", False, "No customers found after creation")
            else:
                self.log_test("Get Customers", False, "Missing expected fields in customers response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Get Customers", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    def test_accounting_transactions(self):
        """Test GET /api/accounting/transactions"""
        response = self.make_request("GET", "/accounting/transactions")
        
        if response and response.status_code == 200:
            result = response.json()
            if "transactions" in result:
                self.log_test("Get Accounting Transactions", True)
                return True
            else:
                self.log_test("Get Accounting Transactions", False, "Missing transactions field in response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Get Accounting Transactions", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    def test_team_members(self):
        """Test GET /api/team/members"""
        response = self.make_request("GET", "/team/members")
        
        if response and response.status_code == 200:
            result = response.json()
            if "members" in result and "count" in result:
                self.log_test("Get Team Members", True)
                return True
            else:
                self.log_test("Get Team Members", False, "Missing expected fields in team response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Get Team Members", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    def test_data_export_all(self):
        """Test POST /api/data/export-all"""
        data = {"format": "json"}
        
        response = self.make_request("POST", "/data/export-all", data)
        
        if response and response.status_code == 200:
            result = response.json()
            if "success" in result and "export_data" in result:
                if result["success"]:
                    self.log_test("Data Export All", True)
                    return True
                else:
                    self.log_test("Data Export All", False, "Export marked as unsuccessful")
            else:
                self.log_test("Data Export All", False, "Missing required fields in export response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Data Export All", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False
    
    def test_audit_logs(self):
        """Test GET /api/security/audit-logs"""
        response = self.make_request("GET", "/security/audit-logs")
        
        if response and response.status_code == 200:
            result = response.json()
            if "audit_logs" in result and "count" in result:
                # Should have audit logs from previous operations
                self.log_test("Get Audit Logs", True)
                return True
            else:
                self.log_test("Get Audit Logs", False, "Missing expected fields in audit response")
        else:
            error_detail = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_test("Get Audit Logs", False, f"Status: {response.status_code if response else 'None'}, Error: {error_detail}")
        return False

    # ============ ERROR HANDLING TESTS ============
    
    def test_auth_error_handling(self):
        """Test endpoints without authentication return 401"""
        # Temporarily clear auth token
        original_token = self.auth_token
        self.auth_token = None
        
        # Test various endpoints should return 401
        endpoints = ["/conversations", "/business/setup", "/documents", "/ai/suggest-reply"]
        success_count = 0
        
        for endpoint in endpoints:
            response = self.make_request("GET", endpoint)
            if response and response.status_code == 401:
                success_count += 1
        
        # Restore auth token
        self.auth_token = original_token
        
        if success_count == len(endpoints):
            self.log_test("Authentication Error Handling", True)
            return True
        else:
            self.log_test("Authentication Error Handling", False, f"Only {success_count}/{len(endpoints)} endpoints returned 401")
        return False
    
    def test_invalid_resource_error_handling(self):
        """Test invalid resource IDs return 404"""
        invalid_conversation_id = "invalid_conversation_id"
        
        response = self.make_request("GET", f"/conversations/{invalid_conversation_id}")
        
        if response and response.status_code == 404:
            self.log_test("Invalid Resource Error Handling", True)
            return True
        else:
            self.log_test("Invalid Resource Error Handling", False, f"Expected 404, got {response.status_code if response else 'None'}")
        return False
    
    # ============ MAIN TEST RUNNER ============
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🚀 Starting TOMI Comprehensive Backend Testing - All Phases (1-7)")
        print(f"📡 Backend URL: {self.base_url}")
        print(f"👤 Test User: {TEST_EMAIL}")
        print("=" * 70)
        
        # Phase 1: Authentication & Onboarding
        print("\n🔐 PHASE 1: AUTHENTICATION & ONBOARDING")
        self.test_user_registration()
        self.test_user_login()
        self.test_get_current_user()
        self.test_business_setup()
        self.test_communication_preferences()
        self.test_onboarding_completion()
        
        # Phase 2: Document Management
        print("\n📄 PHASE 2: DOCUMENT MANAGEMENT")
        self.test_document_upload()
        self.test_get_documents()
        
        # Phase 3: Conversations & Messages
        print("\n💬 PHASE 3: CONVERSATIONS & MESSAGES")
        self.test_create_conversation()
        self.test_get_conversations()
        self.test_add_message()
        self.test_get_conversation_with_messages()
        
        # Phase 4: AI Services
        print("\n🤖 PHASE 4: AI SERVICES")
        self.test_ai_suggest_reply()
        self.test_ai_analyze_message()
        
        # Phase 5: Decision Learning
        print("\n🧠 PHASE 5: DECISION LEARNING")
        self.test_record_decision()
        self.test_get_decision_patterns()
        
        # Phase 6: Automation Management
        print("\n⚙️ PHASE 6: AUTOMATION MANAGEMENT")
        self.test_create_automation()
        self.test_get_automations()
        self.test_toggle_automation()
        
        # Phase 7: Channel Simulator
        print("\n📱 PHASE 7: CHANNEL SIMULATOR")
        self.test_channel_simulator_email()
        self.test_channel_simulator_sms()
        
        # New Enterprise Endpoints
        print("\n🏢 NEW ENTERPRISE ENDPOINTS")
        self.test_chatbot_ask()
        self.test_create_customer()
        self.test_get_customers()
        self.test_accounting_transactions()
        self.test_team_members()
        self.test_data_export_all()
        self.test_audit_logs()
        
        # Error Handling
        print("\n🛡️ ERROR HANDLING TESTS")
        self.test_auth_error_handling()
        self.test_invalid_resource_error_handling()
        
        # Summary
        print("\n" + "=" * 70)
        print(f"📊 TEST RESULTS SUMMARY")
        print(f"Total Tests: {self.results['total_tests']}")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['failed'] > 0:
            print(f"\n🚨 FAILURES:")
            for failure in self.results['failures']:
                print(f"   • {failure['test']}: {failure['details']}")
        
        success_rate = (self.results['passed'] / self.results['total_tests']) * 100 if self.results['total_tests'] > 0 else 0
        print(f"\n📈 Success Rate: {success_rate:.1f}%")
        
        return self.results

if __name__ == "__main__":
    tester = TOMIBackendTester()
    results = tester.run_all_tests()