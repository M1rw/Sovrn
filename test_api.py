#!/usr/bin/env python3
"""Test SOVRN API endpoints"""

import requests
import json

API_URL = "http://localhost:8000"

def test_health():
    """Test API health endpoint"""
    print("\n🔍 Testing API health...")
    response = requests.get(f"{API_URL}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    return response.status_code == 200

def test_inference_health():
    """Test inference service health"""
    print("\n🔍 Testing Inference health...")
    response = requests.get("http://localhost:8080/health")
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Model loaded: {data.get('model_loaded')}")
    if data.get('model_info'):
        print(f"   Model: {data['model_info'].get('name')}")
    return response.status_code == 200 and data.get('model_loaded')

def test_register():
    """Test user registration"""
    print("\n📝 Testing user registration...")
    
    data = {
        "email": "test@example.com",
        "password": "testpassword123",
        "name": "Test User"
    }
    
    try:
        response = requests.post(f"{API_URL}/v1/auth/register", json=data)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            print(f"   ✅ User created: {result.get('email')}")
            return result
        elif response.status_code == 400:
            print(f"   ℹ️  User already exists (OK for testing)")
            return {"email": data["email"]}
        else:
            print(f"   ❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def test_login(email="test@example.com", password="testpassword123"):
    """Test user login"""
    print("\n🔐 Testing user login...")
    
    data = {
        "username": email,
        "password": password
    }
    
    try:
        response = requests.post(f"{API_URL}/v1/auth/login", data=data)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Login successful")
            print(f"   Token: {result.get('access_token')[:20]}...")
            return result.get('access_token')
        else:
            print(f"   ❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def test_create_project(token):
    """Test project creation"""
    print("\n📁 Testing project creation...")
    
    if not token:
        print("   ⚠️  Skipping - no auth token")
        return None
    
    headers = {"Authorization": f"Bearer {token}"}
    
    data = {
        "name": "Test Coffee Shop",
        "brief": "Build a website for a small coffee roastery. They want to sell beans online.",
        "target_pages": ["home", "shop", "about", "contact"]
    }
    
    try:
        response = requests.post(f"{API_URL}/v1/projects", json=data, headers=headers)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            print(f"   ✅ Project created: {result.get('name')}")
            print(f"   ID: {result.get('id')}")
            return result
        else:
            print(f"   ❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def main():
    """Run all API tests"""
    print("\n" + "="*60)
    print("🚀 SOVRN API TEST SUITE")
    print("="*60)
    
    # Test 1: API Health
    api_ok = test_health()
    if not api_ok:
        print("\n❌ API not healthy - cannot continue")
        return False
    
    # Test 2: Inference Health
    inference_ok = test_inference_health()
    if not inference_ok:
        print("\n⚠️  Inference service not ready")
    
    # Test 3: User Registration
    user = test_register()
    
    # Test 4: User Login
    token = test_login()
    if not token:
        print("\n❌ Cannot test projects without auth token")
        return False
    
    # Test 5: Create Project
    project = test_create_project(token)
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"✅ API Health:        {'PASS' if api_ok else 'FAIL'}")
    print(f"✅ Inference Health:  {'PASS' if inference_ok else 'FAIL'}")
    print(f"✅ User Registration: {'PASS' if user else 'FAIL'}")
    print(f"✅ User Login:        {'PASS' if token else 'FAIL'}")
    print(f"✅ Create Project:    {'PASS' if project else 'FAIL'}")
    print("="*60)
    
    success = all([api_ok, user, token, project])
    if success:
        print("\n🎉 All API tests passed!")
    else:
        print("\n⚠️  Some tests failed - check logs above")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted")
        exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
