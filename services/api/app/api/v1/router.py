# =============================================================================
# SOVRN API - Main Router
# =============================================================================
"""
API v1 router aggregating all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, projects, jobs, sparks, templates, locales, admin, internal, ai

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(ai.router, prefix="/ai", tags=["AI"])  # AI endpoints first
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(sparks.router, prefix="/sparks", tags=["Sparks"])
api_router.include_router(templates.router, prefix="/templates", tags=["Templates"])
api_router.include_router(locales.router, prefix="/locales", tags=["Locales"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(internal.router, prefix="/internal", tags=["Internal"])
