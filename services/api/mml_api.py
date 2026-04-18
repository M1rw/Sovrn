#!/usr/bin/env python3
"""
SOVRN MML API Server
====================
Clean, custom AI-powered website generation using Phi-3.
No external AI dependencies - everything runs locally.
"""

import os
import sys
import json
import time
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.lib.ai.mml_engine import MMLEngine, MMLConfig, WebsiteStyle, get_mml_engine


LEGACY_CHAT_DEPRECATION_RESPONSE = {
    "detail": "Deprecated endpoint. Use canonical conversation path POST /api/v1/ai/chat on the main API service.",
    "type": "deprecated_endpoint",
    "canonical_path": "/api/v1/ai/chat",
    "canonical_service": "services/api/app/api/v1/endpoints/ai.py::chat_completion",
}


# =============================================================================
# Data Storage
# =============================================================================

DATA_DIR = Path("/workspaces/Sovrn/data")
PROJECTS_FILE = DATA_DIR / "projects.json"


def _parse_cors_origins(raw_value: Optional[str]) -> List[str]:
    if not raw_value:
        return ["http://localhost:3000", "http://localhost:8000"]

    parsed = [origin.strip() for origin in raw_value.split(",") if origin.strip()]
    return parsed or ["http://localhost:3000", "http://localhost:8000"]

def ensure_storage():
    """Initialize file storage."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PROJECTS_FILE.exists():
        PROJECTS_FILE.write_text("[]")

def load_projects() -> List[Dict]:
    """Load projects from file."""
    ensure_storage()
    try:
        return json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

def save_projects(projects: List[Dict]):
    """Save projects to file."""
    ensure_storage()
    PROJECTS_FILE.write_text(json.dumps(projects, indent=2, default=str), encoding="utf-8")


# =============================================================================
# Global Engine
# =============================================================================

mml_engine: Optional[MMLEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown handler."""
    global mml_engine
    
    print("\n" + "="*60)
    print("  SOVRN MML Engine Starting")
    print("="*60 + "\n")
    
    # Initialize storage
    ensure_storage()
    print(f"✓ Data storage: {DATA_DIR}")
    
    # Load MML Engine
    model_path = os.getenv(
        "PHI3_MODEL_PATH", 
        "/workspaces/Sovrn/models/phi-3-mini-4k-instruct-q4.gguf"
    )
    
    if Path(model_path).exists():
        config = MMLConfig(model_path=model_path)
        mml_engine = MMLEngine(config)
        
        print(f"⏳ Loading Phi-3 model...")
        success = await mml_engine.load()
        
        if success:
            print(f"✓ MML Engine loaded: {model_path}")
        else:
            print(f"✗ Failed to load model")
    else:
        print(f"⚠ Model not found: {model_path}")
        mml_engine = None
    
    print("\n" + "-"*60)
    print(f"  Server ready at http://localhost:8000")
    print(f"  Docs at http://localhost:8000/docs")
    print("-"*60 + "\n")
    
    yield
    
    print("\n✓ MML Engine shutdown complete")


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="SOVRN MML API",
    description="Custom AI-powered website generation engine",
    version="1.0.0",
    lifespan=lifespan
)

_cors_origins = _parse_cors_origins(
    os.getenv("MML_API_CORS_ORIGINS") or os.getenv("CORS_ORIGINS")
)
_allow_credentials = "*" not in _cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Request/Response Models
# =============================================================================

class GenerateRequest(BaseModel):
    """Website generation request."""
    prompt: str = Field(..., description="Website description")
    style: str = Field(default="modern", description="Website style")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "A landing page for a coffee shop called 'Bean There'",
                "style": "modern"
            }
        }


class ChatRequest(BaseModel):
    """Chat request."""
    message: str
    history: Optional[List[Dict[str, str]]] = None


class ProjectCreate(BaseModel):
    """Project creation."""
    name: str
    html: str
    prompt: Optional[str] = ""


class ProjectUpdate(BaseModel):
    """Project update."""
    name: Optional[str] = None
    html: Optional[str] = None


# =============================================================================
# Health Routes
# =============================================================================

@app.get("/")
async def root():
    """API info."""
    return {
        "name": "SOVRN MML API",
        "version": "1.0.0",
        "engine": "Phi-3 MML",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "mml_loaded": mml_engine is not None and mml_engine.is_loaded,
        "timestamp": datetime.now().isoformat()
    }


# =============================================================================
# MML Generation Routes
# =============================================================================

@app.get("/api/v1/ai/status")
async def ai_status():
    """Get AI engine status."""
    return {
        "initialized": mml_engine is not None and mml_engine.is_loaded,
        "engine": "SOVRN MML",
        "model": "phi-3-mini-4k-instruct",
        "capabilities": [
            "website_generation",
            "html_css_js",
            "responsive_design",
            "multiple_styles"
        ],
        "styles": [s.value for s in WebsiteStyle]
    }


@app.post("/api/v1/ai/generate")
async def generate_website(request: GenerateRequest):
    """Generate a complete website from a prompt."""
    
    if mml_engine is None or not mml_engine.is_loaded:
        raise HTTPException(status_code=503, detail="MML Engine not loaded")
    
    # Parse style
    try:
        style = WebsiteStyle(request.style.lower())
    except ValueError:
        style = WebsiteStyle.MODERN
    
    # Generate
    result = await mml_engine.generate(
        prompt=request.prompt,
        style=style
    )
    
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error or "Generation failed")
    
    return {
        "success": True,
        "html": result.html,
        "generation_time_ms": result.generation_time_ms,
        "tokens_used": result.tokens_used,
        "style": style.value
    }


@app.post("/api/v1/ai/chat")
async def chat(request: ChatRequest):
    """Deprecated duplicate chat endpoint. Use canonical main API endpoint instead."""
    _ = request
    return JSONResponse(status_code=410, content=LEGACY_CHAT_DEPRECATION_RESPONSE)


# =============================================================================
# WebSocket for Streaming
# =============================================================================

@app.websocket("/api/v1/ai/stream")
async def websocket_generate(websocket: WebSocket):
    """WebSocket for streaming generation (future enhancement)."""
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if mml_engine is None or not mml_engine.is_loaded:
                await websocket.send_json({"error": "MML Engine not loaded"})
                continue
            
            prompt = data.get("prompt", "")
            style_str = data.get("style", "modern")
            
            try:
                style = WebsiteStyle(style_str.lower())
            except ValueError:
                style = WebsiteStyle.MODERN
            
            # Send status
            await websocket.send_json({"status": "generating"})
            
            result = await mml_engine.generate(prompt=prompt, style=style)
            
            await websocket.send_json({
                "status": "complete",
                "success": result.success,
                "html": result.html,
                "generation_time_ms": result.generation_time_ms,
                "error": result.error
            })
            
    except WebSocketDisconnect:
        pass


# =============================================================================
# Projects Routes
# =============================================================================

@app.get("/api/v1/projects")
async def list_projects():
    """List all saved projects."""
    projects = load_projects()
    return {"projects": projects, "count": len(projects)}


@app.get("/api/v1/projects/{project_id}")
async def get_project(project_id: str):
    """Get a specific project."""
    projects = load_projects()
    project = next((p for p in projects if p["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.post("/api/v1/projects")
async def create_project(project: ProjectCreate):
    """Create a new project."""
    projects = load_projects()
    
    new_project = {
        "id": f"proj_{int(time.time()*1000)}",
        "name": project.name,
        "html": project.html,
        "prompt": project.prompt,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    projects.append(new_project)
    save_projects(projects)
    
    return {"success": True, "project": new_project}


@app.put("/api/v1/projects/{project_id}")
async def update_project(project_id: str, update: ProjectUpdate):
    """Update a project."""
    projects = load_projects()
    project = next((p for p in projects if p["id"] == project_id), None)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if update.name:
        project["name"] = update.name
    if update.html:
        project["html"] = update.html
    project["updated_at"] = datetime.now().isoformat()
    
    save_projects(projects)
    return {"success": True, "project": project}


@app.delete("/api/v1/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project."""
    projects = load_projects()
    projects = [p for p in projects if p["id"] != project_id]
    save_projects(projects)
    return {"success": True}


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "mml_api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
