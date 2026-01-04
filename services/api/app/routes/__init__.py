"""API route handlers."""
from .auth import router as auth_router
from .users import router as users_router
from .projects import router as projects_router
from .jobs import router as jobs_router
from .sparks import router as sparks_router
from .templates import router as templates_router
from .locales import router as locales_router
from .admin import router as admin_router

__all__ = [
    "auth_router",
    "users_router",
    "projects_router",
    "jobs_router",
    "sparks_router",
    "templates_router",
    "locales_router",
    "admin_router",
]
