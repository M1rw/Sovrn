"""
SOVRN AI API - Simple version with file-based storage
Works without external database
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
import uuid

app = FastAPI(title="SOVRN AI API", version="1.0.0")

# CORS - allow all for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data storage path
DATA_DIR = Path("/workspaces/Sovrn/data")
DATA_DIR.mkdir(exist_ok=True)
PROJECTS_FILE = DATA_DIR / "projects.json"
USERS_FILE = DATA_DIR / "users.json"

# Import AI engines
try:
    from app.lib.ai.phi3_client import Phi3LocalAI
    PHI3_AVAILABLE = True
except ImportError:
    PHI3_AVAILABLE = False
    print("⚠️ Phi3 not available")

# Import MML Engine
try:
    from app.lib.ai.mml_engine import MMLEngine, WebsiteStyle
    MML_AVAILABLE = True
except ImportError:
    MML_AVAILABLE = False
    print("⚠️ MML Engine not available")

# Import Advanced MML Engine
try:
    from app.lib.ai.advanced_mml import AdvancedMMLEngine
    ADVANCED_MML_AVAILABLE = True
except ImportError:
    ADVANCED_MML_AVAILABLE = False
    print("⚠️ Advanced MML Engine not available")

# Global AI instances
phi3_ai = None
mml_engine = None
advanced_mml = None

# ============================================================================
# Models
# ============================================================================

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    provider: Optional[str] = "auto"
    temperature: Optional[float] = 0.7

class ChatResponse(BaseModel):
    content: str
    provider: str
    model: str
    success: bool
    latency_ms: Optional[int] = None


LEGACY_CHAT_DEPRECATION_RESPONSE = {
    "detail": "Deprecated endpoint. Use canonical conversation path POST /api/v1/ai/chat on the main API service.",
    "type": "deprecated_endpoint",
    "canonical_path": "/api/v1/ai/chat",
    "canonical_service": "services/api/app/api/v1/endpoints/ai.py::chat_completion",
}

class Project(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    html: Optional[str] = ""
    prompt: Optional[str] = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class User(BaseModel):
    id: Optional[str] = None
    email: str
    name: Optional[str] = ""
    created_at: Optional[str] = None

# ============================================================================
# Data helpers
# ============================================================================

def load_json(path: Path) -> Dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}

def save_json(path: Path, data: Dict):
    path.write_text(json.dumps(data, indent=2))

# ============================================================================
# Startup
# ============================================================================

@app.on_event("startup")
async def startup():
    global phi3_ai, mml_engine, advanced_mml
    
    # Load Advanced MML Engine (preferred for website generation)
    if ADVANCED_MML_AVAILABLE:
        try:
            advanced_mml = AdvancedMMLEngine()
            await advanced_mml.load()
            print("✅ Advanced MML Engine loaded successfully")
        except Exception as e:
            print(f"⚠️ Failed to load Advanced MML Engine: {e}")
    
    # Load MML Engine as fallback for website generation
    if MML_AVAILABLE and not advanced_mml:
        try:
            mml_engine = MMLEngine()
            await mml_engine.load()
            print("✅ MML Engine loaded successfully")
        except Exception as e:
            print(f"⚠️ Failed to load MML Engine: {e}")
    
    # Load Phi-3 for chat (always try to load for conversational features)
    if PHI3_AVAILABLE:
        try:
            phi3_ai = Phi3LocalAI()
            await phi3_ai.load()
            print("✅ Phi-3 loaded successfully for chat")
        except Exception as e:
            print(f"⚠️ Failed to load Phi-3: {e}")
    
    # Initialize data files
    if not PROJECTS_FILE.exists():
        save_json(PROJECTS_FILE, {"projects": []})
    if not USERS_FILE.exists():
        save_json(USERS_FILE, {"users": []})
    print("✅ Data storage initialized")

# ============================================================================
# AI Endpoints
# ============================================================================

class MMLRequest(BaseModel):
    prompt: str
    style: Optional[str] = "modern"

class GeneratedFile(BaseModel):
    name: str
    content: str
    type: str  # "html", "css", "js", "json"
    size: int

class MMLResponse(BaseModel):
    html: str  # Combined preview HTML
    success: bool
    generation_time_ms: Optional[int] = None
    fallback: Optional[bool] = False
    files: Optional[List[GeneratedFile]] = None  # Individual files
    design_style: Optional[str] = None

@app.get("/api/v1/ai/status")
async def ai_status():
    """Get AI status."""
    return {
        "initialized": True,
        "providers": {
            "mml": {
                "available": mml_engine is not None and mml_engine.is_loaded if MML_AVAILABLE else False,
                "model": "phi-3-mini-4k-instruct (MML optimized)"
            },
            "phi3": {
                "available": phi3_ai is not None and phi3_ai.is_loaded if PHI3_AVAILABLE else False,
                "model": "phi-3-mini-4k-instruct"
            }
        },
        "stats": {
            "total_requests": 0
        }
    }

@app.post("/api/v1/mml/generate", response_model=MMLResponse)
async def generate_website(request: MMLRequest):
    """Generate a website using Advanced MML Engine with multi-file output."""
    import time
    start = time.time()
    
    # Try Advanced MML Engine first (multi-file creative output)
    if advanced_mml:
        try:
            result = await advanced_mml.generate(request.prompt)
            latency = int((time.time() - start) * 1000)
            
            if result.get("success"):
                # Convert files dict to list of GeneratedFile objects
                files = []
                raw_files = result.get("files", {})
                for name, content in raw_files.items():
                    file_type = name.split(".")[-1] if "." in name else "txt"
                    files.append(GeneratedFile(
                        name=name,
                        content=content,
                        type=file_type,
                        size=len(content.encode('utf-8'))
                    ))
                
                return MMLResponse(
                    html=result.get("preview_html", result.get("files", {}).get("index.html", "")),
                    success=True,
                    generation_time_ms=latency,
                    fallback=False,
                    files=files,
                    design_style=result.get("design_style", "modern")
                )
        except Exception as e:
            print(f"Advanced MML generation error: {e}")
            import traceback
            traceback.print_exc()
    
    # Fallback to basic MML Engine
    if mml_engine and mml_engine.is_loaded:
        try:
            # Map style string to enum
            style_map = {
                "modern": WebsiteStyle.MODERN,
                "minimal": WebsiteStyle.MINIMAL,
                "bold": WebsiteStyle.BOLD,
                "elegant": WebsiteStyle.ELEGANT,
                "playful": WebsiteStyle.PLAYFUL,
                "corporate": WebsiteStyle.CORPORATE,
                "dark": WebsiteStyle.DARK,
                "light": WebsiteStyle.LIGHT,
            }
            style = style_map.get(request.style.lower(), WebsiteStyle.MODERN)
            
            result = await mml_engine.generate(request.prompt, style=style)
            
            if result.success and result.html:
                return MMLResponse(
                    html=result.html,
                    success=True,
                    generation_time_ms=result.generation_time_ms,
                    fallback=True,  # Mark as fallback since it's not advanced
                    files=[GeneratedFile(
                        name="index.html",
                        content=result.html,
                        type="html",
                        size=len(result.html.encode('utf-8'))
                    )]
                )
        except Exception as e:
            print(f"MML generation error: {e}")
    
    # Fallback to template-based generation
    html = generate_fallback_html(request.prompt)
    latency = int((time.time() - start) * 1000)
    
    return MMLResponse(
        html=html,
        success=True,
        generation_time_ms=latency,
        fallback=True,
        files=[GeneratedFile(
            name="index.html",
            content=html,
            type="html",
            size=len(html.encode('utf-8'))
        )]
    )

def generate_fallback_html(prompt: str) -> str:
    """Generate fallback HTML when AI is not available."""
    title = ' '.join(prompt.split()[:5]).title()
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        :root {{
            --bg: #0a0a0a;
            --fg: #fafafa;
            --muted: #71717a;
            --accent: #3b82f6;
            --card: #18181b;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--fg);
            min-height: 100vh;
        }}
        nav {{
            position: sticky;
            top: 0;
            background: rgba(10, 10, 10, 0.8);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        nav .logo {{
            font-weight: 600;
            font-size: 1.25rem;
        }}
        nav .links {{
            display: flex;
            gap: 2rem;
        }}
        nav a {{
            color: var(--muted);
            text-decoration: none;
            transition: color 0.2s;
        }}
        nav a:hover {{
            color: var(--fg);
        }}
        .hero {{
            max-width: 800px;
            margin: 0 auto;
            padding: 8rem 2rem;
            text-align: center;
        }}
        .hero h1 {{
            font-size: 3.5rem;
            font-weight: 700;
            line-height: 1.1;
            margin-bottom: 1.5rem;
            background: linear-gradient(135deg, #fff 0%, #71717a 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .hero p {{
            font-size: 1.25rem;
            color: var(--muted);
            margin-bottom: 2rem;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
        }}
        .hero button {{
            background: var(--fg);
            color: var(--bg);
            border: none;
            padding: 0.875rem 2rem;
            border-radius: 0.5rem;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: transform 0.2s, opacity 0.2s;
        }}
        .hero button:hover {{
            opacity: 0.9;
            transform: translateY(-1px);
        }}
        .features {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 4rem 2rem;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
        }}
        .card {{
            background: var(--card);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 1rem;
            padding: 2rem;
            transition: transform 0.2s, border-color 0.2s;
        }}
        .card:hover {{
            transform: translateY(-4px);
            border-color: rgba(255,255,255,0.2);
        }}
        .card .icon {{
            width: 3rem;
            height: 3rem;
            background: rgba(59, 130, 246, 0.2);
            border-radius: 0.75rem;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 1rem;
            font-size: 1.5rem;
        }}
        .card h3 {{
            font-size: 1.125rem;
            margin-bottom: 0.5rem;
        }}
        .card p {{
            color: var(--muted);
            font-size: 0.875rem;
            line-height: 1.6;
        }}
        footer {{
            border-top: 1px solid rgba(255,255,255,0.1);
            padding: 2rem;
            text-align: center;
            color: var(--muted);
            font-size: 0.875rem;
        }}
    </style>
</head>
<body>
    <nav>
        <div class="logo">{title}</div>
        <div class="links">
            <a href="#">Home</a>
            <a href="#">Features</a>
            <a href="#">About</a>
            <a href="#">Contact</a>
        </div>
    </nav>
    
    <section class="hero">
        <h1>{title}</h1>
        <p>Welcome to our platform. We're building something amazing that will transform the way you work.</p>
        <button>Get Started</button>
    </section>
    
    <section class="features">
        <div class="card">
            <div class="icon">⚡</div>
            <h3>Lightning Fast</h3>
            <p>Built for performance with optimized code and modern architecture.</p>
        </div>
        <div class="card">
            <div class="icon">🛡️</div>
            <h3>Secure by Design</h3>
            <p>Enterprise-grade security with end-to-end encryption.</p>
        </div>
        <div class="card">
            <div class="icon">🎨</div>
            <h3>Beautiful UI</h3>
            <p>Carefully crafted interface with attention to every detail.</p>
        </div>
    </section>
    
    <footer>
        <p>&copy; 2025 {title}. All rights reserved.</p>
    </footer>
</body>
</html>'''

@app.post("/api/v1/ai/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Deprecated duplicate chat endpoint. Use canonical main API endpoint instead."""
    _ = request
    return JSONResponse(status_code=410, content=LEGACY_CHAT_DEPRECATION_RESPONSE)

# ============================================================================
# Projects Endpoints
# ============================================================================

@app.get("/api/v1/projects")
async def list_projects():
    """List all projects."""
    data = load_json(PROJECTS_FILE)
    return {"projects": data.get("projects", []), "total": len(data.get("projects", []))}

@app.post("/api/v1/projects")
async def create_project(project: Project):
    """Create a new project."""
    data = load_json(PROJECTS_FILE)
    
    new_project = {
        "id": str(uuid.uuid4()),
        "name": project.name,
        "description": project.description,
        "html": project.html,
        "prompt": project.prompt,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    data["projects"].append(new_project)
    save_json(PROJECTS_FILE, data)
    
    return new_project

@app.get("/api/v1/projects/{project_id}")
async def get_project(project_id: str):
    """Get a project by ID."""
    data = load_json(PROJECTS_FILE)
    for p in data.get("projects", []):
        if p["id"] == project_id:
            return p
    raise HTTPException(status_code=404, detail="Project not found")

@app.put("/api/v1/projects/{project_id}")
async def update_project(project_id: str, project: Project):
    """Update a project."""
    data = load_json(PROJECTS_FILE)
    for i, p in enumerate(data.get("projects", [])):
        if p["id"] == project_id:
            data["projects"][i].update({
                "name": project.name,
                "description": project.description,
                "html": project.html,
                "prompt": project.prompt,
                "updated_at": datetime.now().isoformat()
            })
            save_json(PROJECTS_FILE, data)
            return data["projects"][i]
    raise HTTPException(status_code=404, detail="Project not found")

@app.delete("/api/v1/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project."""
    data = load_json(PROJECTS_FILE)
    data["projects"] = [p for p in data.get("projects", []) if p["id"] != project_id]
    save_json(PROJECTS_FILE, data)
    return {"success": True}

# ============================================================================
# Health
# ============================================================================

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mml_loaded": mml_engine is not None and mml_engine.is_loaded if MML_AVAILABLE else False,
        "phi3_loaded": phi3_ai is not None and phi3_ai.is_loaded if PHI3_AVAILABLE else False,
        "storage": "file-based"
    }

@app.get("/")
async def root():
    return {
        "name": "SOVRN AI API",
        "version": "1.0.0",
        "docs": "/docs"
    }

# ============================================================================
# Auth Stubs (to prevent 404s from frontend)
# ============================================================================

@app.get("/api/auth/session")
async def auth_session():
    """Stub for auth session - returns no session."""
    return {"user": None}

@app.post("/api/auth/_log")
async def auth_log():
    """Stub for auth logging."""
    return {"ok": True}

@app.get("/api/auth/csrf")
async def auth_csrf():
    """Stub for CSRF token."""
    return {"csrfToken": "stub"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
