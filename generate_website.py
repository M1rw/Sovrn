#!/usr/bin/env python3
"""
SOVRN Website Generation Test
Tests the complete pipeline: Strategist → Designer → Engineer
"""

import requests
import json
import time
from datetime import datetime

# Configuration
API_BASE = "http://localhost:8000"
API_V1 = f"{API_BASE}/api/v1"

# Test data
TEST_USER = {
    "email": f"test_{int(time.time())}@example.com",
    "password": "TestPassword123!",
    "full_name": "Test User"
}

PROJECT_DATA = {
    "name": "Coffee Shop Website",
    "description": "A modern coffee shop website with menu and contact info"
}

GENERATION_REQUEST = {
    "prompt": "Create a beautiful coffee shop website called 'Brew Haven'. Include a hero section with coffee imagery, an about section describing artisanal coffee, a menu section with 6 popular drinks (espresso, cappuccino, latte, mocha, americano, cold brew) with prices, and a contact section with opening hours. Use warm brown and cream colors. Make it modern and inviting.",
    "requirements": {
        "style": "modern",
        "colors": ["#8B4513", "#D2691E", "#F5DEB3"],
        "sections": ["hero", "about", "menu", "contact"],
        "responsive": True
    }
}


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def print_result(label, data):
    """Print formatted result"""
    print(f"\n✓ {label}:")
    if isinstance(data, dict):
        print(json.dumps(data, indent=2))
    else:
        print(f"  {data}")


def test_health():
    """Test API health"""
    print_section("1. Testing API Health")
    
    response = requests.get(f"{API_BASE}/health")
    print_result("Health Check", response.json())
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print("✅ API is healthy")


def register_user():
    """Register a new test user"""
    print_section("2. Registering Test User")
    
    response = requests.post(
        f"{API_V1}/auth/register",
        json=TEST_USER
    )
    
    if response.status_code == 201:
        data = response.json()
        print_result("Registration Successful", {
            "user_id": data.get("id"),
            "email": data.get("email"),
            "full_name": data.get("full_name")
        })
        print("✅ User registered successfully")
        return data
    elif response.status_code == 400 and "already exists" in response.text.lower():
        print("⚠️  User already exists, will use existing account")
        return None
    else:
        print(f"❌ Registration failed: {response.status_code}")
        print(response.text)
        return None


def login_user():
    """Login and get JWT token"""
    print_section("3. Logging In")
    
    response = requests.post(
        f"{API_V1}/auth/login",
        json={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"]
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        print_result("Login Successful", {
            "token_type": data.get("token_type"),
            "access_token": token[:20] + "..." if token else None
        })
        print("✅ Logged in successfully")
        return token
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None


def create_project(token):
    """Create a new project"""
    print_section("4. Creating Project")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{API_V1}/projects",
        headers=headers,
        json=PROJECT_DATA
    )
    
    if response.status_code == 201:
        data = response.json()
        print_result("Project Created", {
            "project_id": data.get("id"),
            "name": data.get("name"),
            "description": data.get("description"),
            "created_at": data.get("created_at")
        })
        print("✅ Project created successfully")
        return data
    else:
        print(f"❌ Project creation failed: {response.status_code}")
        print(response.text)
        return None


def generate_website(token, project_id):
    """Submit website generation request"""
    print_section("5. Generating Website (AI Pipeline)")
    
    print("\n🤖 Starting AI Pipeline:")
    print("   Step 1: Strategist - Analyzing requirements and creating strategy")
    print("   Step 2: Designer - Creating design specifications and layout")
    print("   Step 3: Engineer - Generating HTML/CSS/JavaScript code")
    print("\n⏳ This may take 30-60 seconds...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{API_V1}/projects/{project_id}/generate",
        headers=headers,
        json=GENERATION_REQUEST
    )
    
    if response.status_code in [200, 201, 202]:
        data = response.json()
        job_id = data.get("job_id") or data.get("id")
        print_result("Generation Started", {
            "job_id": job_id,
            "status": data.get("status"),
            "message": data.get("message", "Generation job queued")
        })
        print("✅ Generation request submitted")
        return job_id
    else:
        print(f"❌ Generation failed: {response.status_code}")
        print(response.text)
        return None


def check_job_status(token, job_id):
    """Check generation job status"""
    print_section("6. Monitoring Job Status")
    
    headers = {"Authorization": f"Bearer {token}"}
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        response = requests.get(
            f"{API_V1}/jobs/{job_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            progress = data.get("progress", 0)
            
            print(f"\r⏳ Status: {status} | Progress: {progress}%", end="", flush=True)
            
            if status == "completed":
                print("\n")
                print_result("Job Completed", {
                    "job_id": job_id,
                    "status": status,
                    "progress": f"{progress}%",
                    "completed_at": data.get("completed_at")
                })
                print("✅ Website generated successfully!")
                return data
            elif status == "failed":
                print("\n")
                print(f"❌ Job failed: {data.get('error')}")
                return None
            
            time.sleep(2)
            attempt += 1
        else:
            print(f"\n❌ Status check failed: {response.status_code}")
            return None
    
    print("\n⏱️  Timeout waiting for job completion")
    return None


def get_generated_website(token, project_id, generation_id):
    """Retrieve the generated website code"""
    print_section("7. Retrieving Generated Website")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_V1}/projects/{project_id}/generations/{generation_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        
        # Extract key information
        result = {
            "generation_id": generation_id,
            "status": data.get("status"),
            "created_at": data.get("created_at"),
        }
        
        # Check for generated files
        files = data.get("files", {})
        if files:
            result["files"] = list(files.keys())
            result["file_count"] = len(files)
        
        # Check for design data
        design = data.get("design", {})
        if design:
            result["design"] = {
                "colors": design.get("colors", [])[:3],
                "fonts": design.get("fonts", [])[:2],
                "layout": design.get("layout", "unknown")
            }
        
        print_result("Generation Details", result)
        
        # Save files to disk
        if files:
            print("\n📁 Saving generated files...")
            output_dir = f"./generated_website_{int(time.time())}"
            import os
            os.makedirs(output_dir, exist_ok=True)
            
            for filename, content in files.items():
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'w') as f:
                    f.write(content)
                print(f"   ✓ Saved: {filename} ({len(content)} bytes)")
            
            print(f"\n✅ Files saved to: {output_dir}/")
        
        print("✅ Website retrieved successfully!")
        return data
    else:
        print(f"❌ Retrieval failed: {response.status_code}")
        print(response.text)
        return None


def main():
    """Run the complete website generation test"""
    print("\n" + "🚀 " * 30)
    print("  SOVRN AI Website Generation Test")
    print("  Testing: Strategist → Designer → Engineer Pipeline")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🚀 " * 30)
    
    try:
        # Step 1: Health check
        test_health()
        
        # Step 2: Register user
        register_user()
        
        # Step 3: Login
        token = login_user()
        if not token:
            print("❌ Cannot proceed without authentication token")
            return
        
        # Step 4: Create project
        project = create_project(token)
        if not project:
            print("❌ Cannot proceed without project")
            return
        
        project_id = project.get("id")
        
        # Step 5: Generate website
        job_id = generate_website(token, project_id)
        if not job_id:
            print("❌ Cannot proceed without job ID")
            return
        
        # Step 6: Monitor job
        job_result = check_job_status(token, job_id)
        if not job_result:
            print("❌ Job did not complete successfully")
            return
        
        # Step 7: Retrieve generated website
        generation_id = job_result.get("generation_id") or job_id
        website = get_generated_website(token, project_id, generation_id)
        
        # Final summary
        print_section("🎉 TEST COMPLETE")
        print("\n✅ All steps completed successfully!")
        print("\n📊 Summary:")
        print(f"   • User: {TEST_USER['email']}")
        print(f"   • Project: {PROJECT_DATA['name']}")
        print(f"   • Project ID: {project_id}")
        print(f"   • Job ID: {job_id}")
        print(f"   • Status: {'SUCCESS' if website else 'PARTIAL'}")
        print("\n🌐 The website has been generated by the AI pipeline!")
        print("   Strategist ✓ → Designer ✓ → Engineer ✓")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
