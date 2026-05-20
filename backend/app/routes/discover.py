from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.auth.deps import require_user
from app.routes.dynamic import get_registered_schemas, get_project_schemas
from app.routes.compositions import get_registry
from app.routes.pipelines import get_aggregation_registry

router = APIRouter(prefix="/api/discover", tags=["discover"])


def _builtin_endpoints() -> list[dict]:
    return [
        {"method": "POST", "path": "/api/auth/signup", "group": "auth", "label": "Sign up (self-register)"},
        {"method": "POST", "path": "/api/auth/signin", "group": "auth", "label": "Sign in"},
        {"method": "POST", "path": "/api/auth/register", "group": "auth", "label": "Register (alias)"},
        {"method": "POST", "path": "/api/auth/login", "group": "auth", "label": "Login (alias)"},
        {"method": "POST", "path": "/api/auth/refresh", "group": "auth", "label": "Refresh token"},
        {"method": "POST", "path": "/api/auth/logout", "group": "auth", "label": "Logout"},
        {"method": "GET",  "path": "/api/auth/me", "group": "auth", "label": "Get current user"},
        {"method": "POST", "path": "/api/auth/verify-email", "group": "auth", "label": "Verify email"},
        {"method": "POST", "path": "/api/auth/resend-verification", "group": "auth", "label": "Resend verification email"},
        {"method": "POST", "path": "/api/auth/forgot-password", "group": "auth", "label": "Forgot password"},
        {"method": "POST", "path": "/api/auth/reset-password", "group": "auth", "label": "Reset password"},
        {"method": "POST", "path": "/api/auth/users", "group": "admin", "label": "Create user (admin)"},
        {"method": "GET",  "path": "/api/auth/users", "group": "admin", "label": "List users"},
        {"method": "GET",  "path": "/api/auth/users/{id}", "group": "admin", "label": "Get user by ID"},
        {"method": "PATCH", "path": "/api/auth/users/{id}", "group": "admin", "label": "Update user"},
        {"method": "PATCH", "path": "/api/auth/users/{id}/role", "group": "admin", "label": "Update user role"},
        {"method": "DELETE", "path": "/api/auth/users/{id}", "group": "admin", "label": "Delete user"},
        {"method": "GET",  "path": "/api/roles/permissions", "group": "admin", "label": "List all permissions"},
        {"method": "GET",  "path": "/api/roles", "group": "admin", "label": "List roles"},
        {"method": "POST", "path": "/api/roles", "group": "admin", "label": "Create role"},
        {"method": "GET",  "path": "/api/roles/{id}", "group": "admin", "label": "Get role"},
        {"method": "PUT",  "path": "/api/roles/{id}", "group": "admin", "label": "Update role"},
        {"method": "DELETE", "path": "/api/roles/{id}", "group": "admin", "label": "Delete role"},
        {"method": "POST", "path": "/api/keys/", "group": "developer", "label": "Create API key"},
        {"method": "GET",  "path": "/api/keys/", "group": "developer", "label": "List API keys"},
        {"method": "DELETE", "path": "/api/keys/{id}", "group": "developer", "label": "Delete API key"},
        {"method": "GET",  "path": "/api/storage/list/{collection}", "group": "storage", "label": "List files"},
        {"method": "POST", "path": "/api/storage/upload/{collection}", "group": "storage", "label": "Upload file"},
        {"method": "GET",  "path": "/api/aggregations/templates", "group": "aggregations", "label": "Aggregation templates"},
        {"method": "GET",  "path": "/api/sdk/{model}", "group": "developer", "label": "TypeScript SDK"},
        {"method": "GET",  "path": "/api/sdk/{model}?lang=python", "group": "developer", "label": "Python SDK"},
        {"method": "GET",  "path": "/api/sdk/{model}?lang=javascript", "group": "developer", "label": "JavaScript SDK"},
        {"method": "GET",  "path": "/api/sdk/{model}?lang=curl", "group": "developer", "label": "curl snippets"},
        {"method": "GET",  "path": "/api/projects/", "group": "projects", "label": "List projects"},
        {"method": "POST", "path": "/api/projects/", "group": "projects", "label": "Create project"},
        {"method": "GET",  "path": "/api/projects/{id}", "group": "projects", "label": "Get project"},
        {"method": "PUT",  "path": "/api/projects/{id}", "group": "projects", "label": "Update project"},
        {"method": "DELETE", "path": "/api/projects/{id}", "group": "projects", "label": "Delete project"},
        {"method": "GET",  "path": "/api/health", "group": "system", "label": "Health check"},
    ]


@router.get("/")
async def discover(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
    x_project_id: str | None = Header(None, alias="X-Project-Id"),
):
    endpoints: list[dict] = list(_builtin_endpoints())

    schemas = get_project_schemas(x_project_id) if x_project_id else get_registered_schemas()
    for name, schema in schemas.items():
        group = f"models/{name}"
        col = name
        endpoints.append({"method": "GET",    "path": f"/api/{col}",           "group": group, "label": f"List {col}"})
        endpoints.append({"method": "POST",   "path": f"/api/{col}",           "group": group, "label": f"Create {col}"})
        endpoints.append({"method": "GET",    "path": f"/api/{col}/{{id}}",    "group": group, "label": f"Get {col} by ID"})
        endpoints.append({"method": "PATCH",  "path": f"/api/{col}/{{id}}",    "group": group, "label": f"Update {col}"})
        endpoints.append({"method": "PUT",    "path": f"/api/{col}/{{id}}",    "group": group, "label": f"Replace {col}"})
        endpoints.append({"method": "DELETE", "path": f"/api/{col}/{{id}}",    "group": group, "label": f"Delete {col}"})
        endpoints.append({"method": "POST",   "path": f"/api/{col}/{{id}}/restore", "group": group, "label": f"Restore {col}"})
        endpoints.append({"method": "POST",   "path": f"/api/{col}/bulk", "group": group, "label": f"Bulk create {col}"})
        endpoints.append({"method": "PATCH",  "path": f"/api/{col}/bulk", "group": group, "label": f"Bulk update {col}"})
        endpoints.append({"method": "DELETE", "path": f"/api/{col}/bulk", "group": group, "label": f"Bulk delete {col}"})

    # Composed API endpoints
    for name, comp in get_registry().items():
        endpoints.append({
            "method": comp.method,
            "path": f"/api/composed/{name}",
            "group": "composed",
            "label": f"Composed: {comp.description or name}",
        })

    # Aggregated API endpoints
    for name, info in get_aggregation_registry().items():
        endpoints.append({
            "method": "GET",
            "path": f"/api/aggregated/{name}",
            "group": "aggregated",
            "label": f"Aggregated: {name}",
        })

    return endpoints
