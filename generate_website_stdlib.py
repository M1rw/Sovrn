#!/usr/bin/env python3
"""
SOVRN Website Generation Test (using stdlib only)
Tests the complete pipeline: Strategist → Designer → Engineer
"""

import urllib.request
import urllib.parse
import urllib.error
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
    "brief": "Create a beautiful coffee shop website called 'Brew Haven'. Include a hero section with coffee imagery, an about section describing artisanal coffee, a menu section with 6 popular drinks (espresso, cappuccino, latte, mocha, americano, cold brew) with prices, and a contact section with opening hours. Use warm brown and cream colors. Make it modern and inviting.",
    "locale": "en",
    "industry": "Food & Beverage",
    "business_type": "Coffee Shop",
    "target_audience": {
        "age_range": "25-45",
        "interests": ["coffee", "artisanal", "local business"]
    },
    "goals": ["attract customers", "show menu", "provide contact info"]
}


def http_request(url, method="GET", data=None, headers=None):
    """Make HTTP request using urllib"""
    if headers is None:
        headers = {}
    
    if data is not None:
        data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode('utf-8')
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        try:
            return e.code, json.loads(body)
        except:
            return e.code, {"error": body}
    except Exception as e:
        return 0, {"error": str(e)}


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
    
    status, data = http_request(f"{API_BASE}/health")
    print_result("Health Check", data)
    
    if status == 200 and data.get("status") == "healthy":
        print("✅ API is healthy")
        return True
    else:
        print(f"❌ API health check failed: {status}")
        return False


def register_user():
    """Register a new test user"""
    print_section("2. Registering Test User")
    
    status, data = http_request(
        f"{API_V1}/auth/register",
        method="POST",
        data=TEST_USER
    )
    
    if status == 201:
        print_result("Registration Successful", {
            "user_id": data.get("id"),
            "email": data.get("email"),
            "full_name": data.get("full_name")
        })
        print("✅ User registered successfully")
        return data
    elif status == 400:
        print("⚠️  User may already exist, will attempt login")
        return None
    else:
        print(f"❌ Registration failed: {status}")
        print(json.dumps(data, indent=2))
        return None


def login_user():
    """Login and get JWT token"""
    print_section("3. Logging In")
    
    status, data = http_request(
        f"{API_V1}/auth/login",
        method="POST",
        data={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"]
        }
    )
    
    if status == 200:
        token = data.get("access_token")
        print_result("Login Successful", {
            "token_type": data.get("token_type"),
            "access_token": token[:20] + "..." if token else None
        })
        print("✅ Logged in successfully")
        return token
    else:
        print(f"❌ Login failed: {status}")
        print(json.dumps(data, indent=2))
        return None


def create_project(token):
    """Create a new project"""
    print_section("4. Creating Project")
    
    status, data = http_request(
        f"{API_V1}/projects",
        method="POST",
        data=PROJECT_DATA,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if status == 201:
        print_result("Project Created", {
            "project_id": data.get("id"),
            "name": data.get("name"),
            "description": data.get("description"),
            "created_at": data.get("created_at")
        })
        print("✅ Project created successfully")
        return data
    else:
        print(f"❌ Project creation failed: {status}")
        print(json.dumps(data, indent=2))
        return None


def generate_website(token, project_id):
    """Submit website generation request"""
    print_section("5. Generating Website (AI Pipeline)")
    
    print("\n🤖 Starting AI Pipeline:")
    print("   Step 1: Strategist - Analyzing requirements and creating strategy")
    print("   Step 2: Designer - Creating design specifications and layout")
    print("   Step 3: Engineer - Generating HTML/CSS/JavaScript code")
    print("\n⏳ This may take 30-60 seconds...")
    
    status, data = http_request(
        f"{API_V1}/projects/{project_id}/generate",
        method="POST",
        data=GENERATION_REQUEST,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if status in [200, 201, 202]:
        job_id = data.get("job_id") or data.get("id")
        print_result("Generation Started", {
            "job_id": job_id,
            "status": data.get("status"),
            "message": data.get("message", "Generation job queued")
        })
        print("✅ Generation request submitted")
        return job_id
    else:
        print(f"❌ Generation failed: {status}")
        print(json.dumps(data, indent=2))
        return None


def check_job_status(token, job_id):
    """Check generation job status"""
    print_section("6. Monitoring Job Status")
    
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        status, data = http_request(
            f"{API_V1}/jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if status == 200:
            job_status = data.get("status")
            progress = data.get("progress", 0)
            
            print(f"\r⏳ Status: {job_status} | Progress: {progress}%", end="", flush=True)
            
            if job_status == "completed":
                print("\n")
                print_result("Job Completed", {
                    "job_id": job_id,
                    "status": job_status,
                    "progress": f"{progress}%",
                    "completed_at": data.get("completed_at")
                })
                print("✅ Website generated successfully!")
                return data
            elif job_status == "failed":
                print("\n")
                print(f"❌ Job failed: {data.get('error')}")
                return None
            
            time.sleep(2)
            attempt += 1
        else:
            print(f"\n❌ Status check failed: {status}")
            return None
    
    print("\n⏱️  Timeout waiting for job completion")
    return None


def get_generated_website(token, project_id, generation_id):
    """Retrieve the generated website code"""
    print_section("7. Retrieving Generated Website")
    
    status, data = http_request(
        f"{API_V1}/projects/{project_id}/generations/{generation_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if status == 200:
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
            output_dir = f"/tmp/generated_website_{int(time.time())}"
            import os
            os.makedirs(output_dir, exist_ok=True)
            
            for filename, content in files.items():
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'w') as f:
                    f.write(content)
                size_kb = len(content) / 1024
                print(f"   ✓ Saved: {filename} ({size_kb:.1f} KB)")
            
            print(f"\n✅ Files saved to: {output_dir}/")
        
        print("✅ Website retrieved successfully!")
        return data
    else:
        print(f"❌ Retrieval failed: {status}")
        print(json.dumps(data, indent=2))
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
        if not test_health():
            print("❌ API not healthy, cannot continue")
            return
        
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
            print("⚠️  Job did not complete, but may still be processing")
            print("    Check job status later or review API logs")
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
