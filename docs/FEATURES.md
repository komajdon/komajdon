# Komajdon Feature Catalog

> **Version**: 0.1.0 — **Stack**: FastAPI (Python) + React (TypeScript) + MongoDB + WebSocket

---

## 1. Authentication

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/auth/signup` | POST | Register with email+password; auto-assigns `user` role; returns JWT + refresh token |
| `/api/auth/signin` | POST | Authenticate; account lockout after 5 failures (15-min cooldown) |
| `/api/auth/refresh` | POST | Exchange refresh token for a new JWT pair; old token invalidated |
| `/api/auth/logout` | POST | Invalidate refresh token server-side |
| `/api/auth/verify-email` | POST | Verify email via signed JWT token (7-day expiry) |
| `/api/auth/resend-verification` | POST | Generate new verification token (logged in dev mode) |
| `/api/auth/forgot-password` | POST | Request password reset; token logged in dev mode |
| `/api/auth/reset-password` | POST | Confirm reset with token + new password; invalidates all refresh tokens |
| `/api/auth/me` | GET | Current user profile (email, role, permissions, verification status) |

**Password policy**: minimum 8 chars, requires uppercase, lowercase, digit. Hashed with bcrypt (13 rounds).

**JWT**: HS256 via `python-jose`, access tokens configurable TTL (default 30 min), refresh tokens are opaque random strings, verification tokens carry purpose-embedded `jti`.

---

## 2. Admin — User Management

| Endpoint | Method | Permission | Purpose |
|---|---|---|---|
| `/api/auth/users` | GET | `users:read` | List all users |
| `/api/auth/users` | POST | `users:create` | Admin creates user with role/permissions |
| `/api/auth/users/{id}` | GET | `users:read` | Get user by ID |
| `/api/auth/users/{id}` | PATCH | `users:update` | Update email, is_active, email_verified |
| `/api/auth/users/{id}/role` | PATCH | `users:update` | Change role and permissions |
| `/api/auth/users/{id}` | DELETE | `users:delete` | Delete user (last admin protected) |

---

## 3. Role-Based Access Control (RBAC)

**5 default roles**: `admin` (all permissions), `editor` (data CRUD), `viewer` (read-only), `user` (self-data), plus custom roles.

**27 granular permissions** across 6 domains with wildcard support:
- `users:*` — read, create, update, delete
- `models:*` — read, create, update, delete
- `roles:*` — read, create, update, delete
- `system:*` — health, logs, settings, rate-limits
- `api:access` — base API access
- `{collection}:{action}` — per-collection dynamic permissions

| Endpoint | Method | Permission | Purpose |
|---|---|---|---|
| `/api/roles/` | GET | `roles:read` | List all roles |
| `/api/roles/` | POST | `roles:create` | Create role with custom permissions |
| `/api/roles/{id}` | GET | `roles:read` | Get role by ID |
| `/api/roles/{id}` | PUT | `roles:update` | Update role (default roles protected) |
| `/api/roles/{id}` | DELETE | `roles:delete` | Delete role (default roles protected) |
| `/api/roles/permissions` | GET | `roles:read` | List all permission keys with descriptions |

---

## 4. API Keys

| Endpoint | Method | Permission | Purpose |
|---|---|---|---|
| `/api/keys/` | POST | `api:access` | Create key with name + role; returns `mf_*` key once (stored as hash) |
| `/api/keys/` | GET | `api:access` | List user's keys (truncated preview) |
| `/api/keys/{id}` | DELETE | `api:access` | Delete key |

---

## 5. Projects (Multi-Tenancy)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/projects/` | GET | List accessible projects (admin sees all) |
| `/api/projects/` | POST | Create project with name + slug (slug must be unique) |
| `/api/projects/{id}` | GET | Get project details |
| `/api/projects/{id}` | PUT | Update name/description |
| `/api/projects/{id}` | DELETE | Delete project |

**Isolation**: `X-Project-Id` header scopes models and data; admin, owner, and members have access; compound unique index on `(name, project_id)`.

---

## 6. Data Models (Schemas)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/models/` | GET | List all model schemas (optionally project-scoped) |
| `/api/models/` | POST | Create model with fields, indexes, auth_protected, realtime_enabled |
| `/api/models/{name}` | GET | Get schema by name |
| `/api/models/{name}` | PUT | Update schema with data migration |
| `/api/models/{name}` | DELETE | Delete model and drop collection |
| `/api/models/{name}/export` | GET | Export schema as JSON |
| `/api/models/import` | POST | Import schema from JSON |

**Field types**: string, number, boolean, date, array, object, relation (belongs_to/has_one/has_many). Validation includes required, unique, min/max length, min/max, regex pattern (ReDoS-safe), enum, foreign key resolution, unknown-field rejection.

**Indexes**: custom ASC/DESC/unique per field; auto-created for unique and indexed fields.

---

## 7. Dynamic REST API (Auto-Generated CRUD)

Every model automatically gets 10 endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/{model}` | GET | List with pagination, filtering, sorting, search, projection, populate |
| `/api/{model}` | POST | Create with schema validation |
| `/api/{model}/{id}` | GET | Get by ID with populate |
| `/api/{model}/{id}` | PATCH | Partial update |
| `/api/{model}/{id}` | PUT | Full replace |
| `/api/{model}/{id}` | DELETE | Soft delete (default) or hard delete (`?hard=true`) |
| `/api/{model}/{id}/restore` | POST | Restore soft-deleted document |
| `/api/{model}/bulk` | POST | Bulk create (max 100) |
| `/api/{model}/bulk` | PATCH | Bulk update by IDs (max 100) |
| `/api/{model}/bulk` | DELETE | Bulk delete (max 100, soft or hard) |

**Query capabilities**: cursor & offset pagination, 15+ filter operators (eq, ne, gt, gte, lt, lte, in, nin, regex, contains, near, geo_within, geo_intersects), full-text search, field projection, aggregation shortcuts (count, sum).

**Security**: owner-filtering for auth_protected models, banned operator blocking (`$where`, `$function`, etc.), ReDoS-safe regex, soft-delete filtering.

---

## 8. Aggregation Pipelines

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/pipelines/` | POST | Create named pipeline with ordered stages |
| `/api/pipelines/` | GET | List pipelines |
| `/api/pipelines/{id}` | GET/ PUT/ DELETE | CRUD by ID |
| `/api/pipelines/{id}/run` | POST | Execute and return results |
| `/api/pipelines/{id}/expose` | POST | Expose as `/api/aggregated/{name}` |

**Supported stages**: `$match`, `$group`, `$sort`, `$project`, `$limit`, `$skip`, `$lookup`, `$unwind`, `$count`, `$addFields`. Parameter validation with type checking and bounds; `$lookup` restricted to prevent collection injection.

**Quick templates**: count_by_field, average_by_field, latest_items, group_and_lookup.

---

## 9. API Composer (Multi-Step Orchestration)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/compositions/` | GET | List compositions |
| `/api/compositions/` | POST | Create composition with chained steps |
| `/api/compositions/{name}` | PUT | Update composition |
| `/api/compositions/{name}` | DELETE | Delete composition |
| `/api/composed/{name}` | dynamic | Execute composition |

**Step types**: `request` (internal API call with `{{interpolation}}`), `transform` (pick, omit, rename, compute, filter, sort), `merge` (concat, object, zip). Restricted to `/api/*` paths only.

---

## 10. File Storage (GridFS)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/storage/upload/{collection}` | POST | Upload file (50MB max, MIME-whitelisted) |
| `/api/storage/download/{file_id}` | GET | Download file (owner-scoped) |
| `/api/storage/list/{collection}` | GET | List files (owner-scoped) |
| `/api/storage/delete/{file_id}` | DELETE | Delete file (owner-scoped) |

**Allowed MIME types**: JPEG, PNG, GIF, WebP, SVG, PDF, TXT, CSV, MD, JSON, XML, ZIP, Gzip, XLSX, DOCX.

---

## 11. Real-Time / WebSocket

| Endpoint | Purpose |
|---|---|
| `ws://{host}/ws/{collection}?token={jwt}` | Subscribe to real-time events |

**Events**: `create`, `update`, `replace`, `delete`, `bulk_create`, `ping` (30s heartbeat). Per-collection rooms, auto-cleanup of dead connections.

**Frontend client**: singleton with exponential backoff reconnection (10 attempts, up to 30s), event subscription, auto-disconnect.

---

## 12. Rate Limiting

**Global defaults**: 60 req/min for API, 10 req/min for auth. Sliding window, per-IP.

**Custom rules** (stored in `_rate_limits` collection):

| Endpoint | Method | Permission | Purpose |
|---|---|---|---|
| `/api/rate-limits/` | GET | `system:settings` | List rules |
| `/api/rate-limits/` | POST | `system:settings` | Create rule (endpoint, method, max, window, enabled) |
| `/api/rate-limits/{id}` | PUT | `system:settings` | Update rule |
| `/api/rate-limits/{id}` | DELETE | `system:settings` | Delete rule |

Rules hot-reloaded on change. Supports `*` method matching any HTTP method.

---

## 13. Security & Middleware

| Middleware | Purpose |
|---|---|
| CORS | Configurable origins |
| Security Headers | HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, X-XSS-Protection |
| Audit Log | Logs method, path, status, duration, user, IP for all `/api/*` requests |
| Rate Limiting | Sliding-window per-IP-per-endpoint with rule overrides |

**Additional**: bcrypt (13 rounds), API key hashing, unknown-field rejection, operator injection prevention, ReDoS protection, path traversal prevention, account lockout, soft-delete defaults.

---

## 14. SDK Generation

| Endpoint | Lang | Purpose |
|---|---|---|
| `/api/sdk/{model}?lang=typescript` | TypeScript | Typed client with full CRUD + bulk |
| `/api/sdk/{model}?lang=python` | Python | httpx-based client |
| `/api/sdk/{model}?lang=javascript` | JS | JavaScript client |
| `/api/sdk/{model}?lang=curl` | curl | curl command examples |

Each SDK includes typed interfaces, all CRUD + bulk + restore methods, and JWT Bearer auth.

---

## 15. API Discovery & Health

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/discover/` | GET | All endpoints grouped by category |
| `/api/health` | GET | `{"status": "ok", "service": "komajdon"}` |
| `/` | GET | Admin SPA |

---

## 16. Frontend Pages

| Route | Page | Features |
|---|---|---|
| `/login` | LoginPage | Sign in, sign up, forgot/reset password |
| `/` | DashboardPage | Model grid, import schema, create model |
| `/models/new` | ModelBuilderPage | Visual builder, field editor, indexes, preview |
| `/models/:name` | ModelDetailPage | Schema, playground, aggregations, SDK, real-time |
| `/models/:name/edit` | ModelBuilderPage | Edit existing model |
| `/data` | DataExplorerPage | Collection selector, table, filter, CRUD |
| `/aggregations` | AggregationsPage | Pipeline builder, run, expose |
| `/composer` | ApiComposerPage | Composition builder, step editor, test |
| `/projects` | ProjectsPage | Project grid, create/edit/delete, scope toggle |
| `/users` | UsersPage | User table, role changer, create/delete |
| `/roles` | RolesPage | Role cards, permission picker, CRUD |
| `/keys` | ApiKeysPage | Key list, create with role, copy/delete |
| `/rate-limits` | RateLimitsPage | Rule list, toggle, CRUD |
| `/settings` | SettingsPage | Profile, email verify, password reset |
| `/storage` | StoragePage | Upload, file list, download, delete |

**State management** (Zustand): authStore, modelStore, projectStore, uiStore. **Services**: api.ts (HTTP with auto-refresh + project header), socket.ts (WebSocket singleton with reconnection).

---

## 17. Infrastructure

- **Database**: MongoDB via `motor` (async), GridFS for files, TTL indexes for token cleanup
- **Configuration**: `.env` with 18+ settings via `pydantic-settings`
- **Containerization**: Docker Compose (dev + prod), Dockerfiles for backend
- **Lifespan**: Seeds default roles, loads rate-limit rules, regenerates dynamic routes on startup
- **Error handling**: Global exception handler (500 + log)
- **Static files**: Admin SPA served from `/static/` and `/`
- **Cache**: In-memory with TTL (10s), per-user per-collection, invalidated on mutations
