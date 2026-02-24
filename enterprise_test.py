#!/usr/bin/env python3
"""
Enterprise API Endpoints Testing - Focus on Review Request
Tests the 6 specific enterprise endpoints requested:
1. Chatbot API (/api/chatbot/ask)
2. Customer Management (/api/customers) 
3. Accounting (/api/accounting/transactions)
4. Team/RBAC (/api/team/members)
5. Data Export (/api/data/export-all)
6. Audit Logs (/api/security/audit-logs)
"""

import requests
import json
import uuid

# Configuration
BASE_URL = "https://tomi-chatbot-ai.preview.emergentagent.com/api"

def test_enterprise_endpoints():
    print("🏢 Testing TOMI Enterprise API Endpoints")
    print(f"📡 Backend URL: {BASE_URL}")
    print("=" * 60)
    
    # Step 1: Register a new user
    test_email = f"enterprise.test.{uuid.uuid4().hex[:8]}@example.com"
    test_password = "EnterpriseTest123!"
    
    print("\n🔐 STEP 1: User Registration")
    register_data = {
        "name": "Enterprise Tester",
        "email": test_email,
        "phone": "+1-555-888-9999",
        "password": test_password
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    if response.status_code == 200:
        auth_token = response.json()["token"]
        headers = {"Authorization": f"Bearer {auth_token}"}
        print("✅ User registration successful")
    else:
        print(f"❌ User registration failed: {response.status_code} - {response.text}")
        return
    
    # Step 2: Business Setup
    print("\n🏢 STEP 2: Business Setup")
    business_data = {
        "name": "Enterprise Solutions Inc",
        "business_type": "Technology Consulting",
        "products_services": "Enterprise software consulting, implementation, and support services",
        "working_hours": "Monday-Friday 8AM-6PM EST",
        "locations": ["New York, NY", "San Francisco, CA"],
        "team_size": "50+ employees"
    }
    
    response = requests.post(f"{BASE_URL}/business/setup", json=business_data, headers=headers)
    if response.status_code == 200:
        print("✅ Business setup successful")
    else:
        print(f"❌ Business setup failed: {response.status_code} - {response.text}")
        return
    
    # Step 3: Complete Onboarding
    print("\n📋 STEP 3: Complete Onboarding")
    response = requests.post(f"{BASE_URL}/onboarding/complete", headers=headers)
    if response.status_code == 200:
        print("✅ Onboarding completed successfully")
    else:
        print(f"❌ Onboarding failed: {response.status_code} - {response.text}")
        return
    
    print("\n🎯 TESTING ENTERPRISE ENDPOINTS")
    print("=" * 60)
    
    results = {"passed": 0, "failed": 0, "total": 6}
    
    # Test 1: Chatbot API
    print("\n1️⃣ Testing Chatbot API (/api/chatbot/ask)")
    chatbot_data = {
        "question": "What are our main enterprise consulting services and their typical pricing?",
        "include_web_search": False
    }
    
    response = requests.post(f"{BASE_URL}/chatbot/ask", json=chatbot_data, headers=headers)
    if response.status_code == 200:
        result = response.json()
        if result.get("success") and "answer" in result:
            print("✅ Chatbot API working - generated intelligent business answer")
            results["passed"] += 1
        else:
            print(f"❌ Chatbot API failed - Invalid response structure")
            results["failed"] += 1
    else:
        print(f"❌ Chatbot API failed: {response.status_code} - {response.text[:100]}")
        results["failed"] += 1
    
    # Test 2: Customer Management - Create Customer
    print("\n2️⃣ Testing Customer Management (/api/customers)")
    customer_data = {
        "name": "Microsoft Corporation",
        "email": "partnerships@microsoft.com",
        "phone": "+1-800-642-7676", 
        "address": "One Microsoft Way, Redmond, WA 98052",
        "notes": "Fortune 500 client interested in enterprise consulting services for Azure migration",
        "tags": ["enterprise_client", "azure_migration", "priority"]
    }
    
    response = requests.post(f"{BASE_URL}/customers", json=customer_data, headers=headers)
    if response.status_code == 200:
        result = response.json()
        if result.get("success") and "customer_id" in result:
            customer_id = result["customer_id"]
            
            # Test list customers
            response = requests.get(f"{BASE_URL}/customers", headers=headers)
            if response.status_code == 200:
                customers = response.json()
                if "customers" in customers and len(customers["customers"]) > 0:
                    print("✅ Customer Management working - created and listed customers successfully")
                    results["passed"] += 1
                else:
                    print("❌ Customer Management failed - unable to list customers")
                    results["failed"] += 1
            else:
                print(f"❌ Customer Management failed - list error: {response.status_code}")
                results["failed"] += 1
        else:
            print(f"❌ Customer Management failed - create error")
            results["failed"] += 1
    else:
        print(f"❌ Customer Management failed: {response.status_code} - {response.text[:100]}")
        results["failed"] += 1
    
    # Test 3: Accounting Transactions
    print("\n3️⃣ Testing Accounting (/api/accounting/transactions)")
    response = requests.get(f"{BASE_URL}/accounting/transactions", headers=headers)
    if response.status_code == 200:
        result = response.json()
        if "transactions" in result:
            print("✅ Accounting Transactions working - retrieved transaction data successfully")
            results["passed"] += 1
        else:
            print("❌ Accounting Transactions failed - missing transactions field")
            results["failed"] += 1
    else:
        print(f"❌ Accounting Transactions failed: {response.status_code} - {response.text[:100]}")
        results["failed"] += 1
    
    # Test 4: Team/RBAC Members
    print("\n4️⃣ Testing Team Management (/api/team/members)")
    response = requests.get(f"{BASE_URL}/team/members", headers=headers)
    if response.status_code == 200:
        result = response.json()
        if "members" in result and "count" in result:
            print("✅ Team Members working - retrieved team member data successfully")
            results["passed"] += 1
        else:
            print("❌ Team Members failed - missing required fields")
            results["failed"] += 1
    else:
        print(f"❌ Team Members failed: {response.status_code} - {response.text[:100]}")
        results["failed"] += 1
    
    # Test 5: Data Export
    print("\n5️⃣ Testing Data Export (/api/data/export-all)")
    export_data = {"format": "json"}
    response = requests.post(f"{BASE_URL}/data/export-all", json=export_data, headers=headers)
    if response.status_code == 200:
        result = response.json()
        if result.get("success") and "export" in result:
            export_info = result["export"]
            if "export_id" in export_info and "data" in export_info:
                print("✅ Data Export working - exported all business data successfully")
                results["passed"] += 1
            else:
                print("❌ Data Export failed - missing export structure")
                results["failed"] += 1
        else:
            print("❌ Data Export failed - missing success or export fields")
            results["failed"] += 1
    else:
        print(f"❌ Data Export failed: {response.status_code} - {response.text[:100]}")
        results["failed"] += 1
    
    # Test 6: Audit Logs
    print("\n6️⃣ Testing Audit Logs (/api/security/audit-logs)")
    response = requests.get(f"{BASE_URL}/security/audit-logs", headers=headers)
    if response.status_code == 200:
        result = response.json()
        if "audit_logs" in result and "count" in result:
            print("✅ Audit Logs working - retrieved security audit data successfully")
            results["passed"] += 1
        else:
            print("❌ Audit Logs failed - missing required fields")
            results["failed"] += 1
    else:
        print(f"❌ Audit Logs failed: {response.status_code} - {response.text[:100]}")
        results["failed"] += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 ENTERPRISE ENDPOINTS TEST SUMMARY")
    print(f"Total Tests: {results['total']}")
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    
    success_rate = (results['passed'] / results['total']) * 100
    print(f"📈 Success Rate: {success_rate:.1f}%")
    
    if results['failed'] == 0:
        print("\n🎉 ALL ENTERPRISE ENDPOINTS WORKING PERFECTLY!")
        print("✅ Authentication flow complete")
        print("✅ Business setup complete") 
        print("✅ Onboarding complete")
        print("✅ All 6 enterprise endpoints returning proper JSON responses")
    
    return results

if __name__ == "__main__":
    test_enterprise_endpoints()