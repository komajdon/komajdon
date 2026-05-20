from __future__ import annotations

PERMISSIONS = {
    # ── User Management ───────────────────────────
    "users:read": "View users in the system",
    "users:create": "Create new users manually",
    "users:update": "Update user details and roles",
    "users:delete": "Delete users",
    # ── Model / Collection Access ─────────────────
    "models:read": "View model schemas",
    "models:create": "Create new data models",
    "models:update": "Update model schemas",
    "models:delete": "Delete models",
    # ── Data Access (per-collection, e.g. products:read) ─
    # Dynamic: {collection}:{action}
    # ── Role Management ───────────────────────────
    "roles:read": "View roles and their permissions",
    "roles:create": "Create new roles",
    "roles:update": "Update role permissions",
    "roles:delete": "Delete roles",
    # ── System ────────────────────────────────────
    "system:health": "Access health check endpoints",
    "system:logs": "View audit logs",
    "system:settings": "Manage system settings",
    "system:rate-limits": "Manage per-endpoint rate limit rules",
    # ── API Access ────────────────────────────────
    "api:access": "Access the API (base permission)",
}

COLLECTION_ACTIONS = ["read", "create", "update", "delete"]


def collection_permission(collection: str, action: str) -> str:
    return f"{collection}:{action}"


DEFAULT_ROLES = {
    "admin": {
        "description": "Full system access. Can manage users, roles, models, and all data.",
        "permissions": list(PERMISSIONS.keys()),
        "is_default": False,
    },
    "editor": {
        "description": "Can create and edit content but cannot manage users or system settings.",
        "permissions": [
            "api:access",
            "*:read",
            "*:create",
            "*:update",
            "users:read",
            "models:read",
            "models:create",
            "models:update",
            "roles:read",
            "system:health",
        ],
        "is_default": False,
    },
    "viewer": {
        "description": "Read-only access to models and data.",
        "permissions": [
            "api:access",
            "*:read",
            "users:read",
            "models:read",
            "roles:read",
            "system:health",
        ],
        "is_default": False,
    },
    "user": {
        "description": "Default role for self-registered users. Can access their own data and make purchases.",
        "permissions": [
            "api:access",
            "*:read",
            "system:health",
            "Cart:create",
            "Cart:update",
            "Cart:delete",
            "CartItem:create",
            "CartItem:update",
            "CartItem:delete",
            "Order:create",
            "Order:update",
            "OrderItem:create",
            "Review:create",
            "Review:update",
        ],
        "is_default": True,
    },
}


def has_permission(user: dict | None, required: str) -> bool:
    if not user:
        return False
    if user.get("role") == "admin":
        return True
    user_perms = user.get("permissions", [])
    if required in user_perms:
        return True
    collection, action = required.split(":", 1) if ":" in required else (required, "")
    wildcard = f"*:{action}"
    if wildcard in user_perms:
        return True
    if f"{collection}:*" in user_perms:
        return True
    if "*:*" in user_perms:
        return True
    return False


def has_any_permission(user: dict | None, required: list[str]) -> bool:
    return any(has_permission(user, p) for p in required)
