# Development Guide

Quick reference for common Komajdon development tasks, workflows, and troubleshooting.

---

## Quick Start

### Option A: Docker (recommended)

```bash
cp .env.example .env
# Edit .env — set SECRET_KEY to a secure random value
make dev
```

This starts MongoDB, backend (:8000), and frontend (:5173).

### Option B: Local (without Docker)

```bash
# Terminal 1 — MongoDB
docker run -d --name komajdon-db -p 27017:27017 mongo:7

# Terminal 2 — Backend
cd backend
cp ../.env.example .env
pip install -r requirements-dev.txt
SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3 — Frontend
cd frontend
npm install
npm run dev
```

### Verify

```bash
curl http://localhost:8000/api/health
# → {"status":"ok","database":"connected"}
```

Open `http://localhost:5173` — login page should load.

---

## Development Workflows

### Generate a SECRET_KEY

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Create an admin user

```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"Admin1234!"}'

# Get the email verification token from server logs, then:
curl -X POST http://localhost:8000/api/auth/verify-email \
  -H "Content-Type: application/json" \
  -d '{"token":"<token-from-logs>"}'

# Promote to admin (requires direct MongoDB access)
mongosh komajdon --eval 'db.users.updateOne({email:"admin@example.com"},{$set:{role:"admin"}})'
```

### Seed the shop-website demo project

```bash
# 1. Login and save the token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/signin \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"Admin1234!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
echo "$TOKEN" > /tmp/shop_token.txt

# 2. Run the seed script
python3 setup_shop.py
```

---

## Database

### Access MongoDB directly

```bash
# Docker
docker exec -it komajdon-db mongosh

# Local
mongosh mongodb://localhost:27017
```

### Common queries

```javascript
// List collections
use komajdon
show collections

// Count documents
db.users.countDocuments()
db._schemas.countDocuments()
db.Product.countDocuments()

// List all users
db.users.find().pretty()

// Check project-scoped schemas
db._schemas.find({project_id: {$exists: true}}).pretty()

// Drop everything (reset)
db.dropDatabase()
```

### Reset the database

```bash
docker exec -it komajdon-db mongosh --eval 'db.getSiblingDB("komajdon").dropDatabase()'
# Restart backend to regenerate indexes:
docker restart komajdon-api
```

### Backfill project_id on existing pipelines

```bash
mongosh komajdon --eval '
  const pid = db._projects.findOne({slug:"shop-website"})._id.str;
  db._pipelines.updateMany(
    {project_id: {$exists: false}},
    {$set: {project_id: pid}}
  );
'
```

---

## Testing

### Backend

```bash
# Run all tests
cd backend && python -m pytest tests/ -v

# With coverage
python -m pytest tests/ -v --cov=app --cov-report=term-missing

# Run a specific test file
python -m pytest tests/test_auth.py -v

# Run a specific test
python -m pytest tests/test_auth.py::test_signup -v

# Fast (no coverage)
python -m pytest tests/ -v --tb=short -q
```

Tests use an in-memory MongoDB mock (`mongomock`-like via pytest-asyncio). No real database connection needed.

> **Note:** If `pytest` is not installed, run `pip install -r requirements-dev.txt`.

### Frontend

```bash
cd frontend

# Run all tests
npx vitest run

# Watch mode
npx vitest

# Specific file
npx vitest run --reporter=verbose src/lib/utils.test.ts
```

### Test accounts (after seeding)

| Email | Password | Role |
|-------|----------|------|
| `farnam.farzadkia@gmail.com` | `35ZaYiM6ctHAGLq` | admin |
| `john@example.com` | `ShopAdmin1!` | user |

---

## Common Tasks

### Create a new API endpoint

1. Create `backend/app/routes/my_feature.py`
2. Add a router with `APIRouter(prefix="/api/my-feature", tags=["my-feature"])`
3. Import and include it in `backend/app/main.py`:
   ```python
   from app.routes import my_feature
   app.include_router(my_feature.router)
   ```

### Add a new page to the frontend

1. Create `frontend/src/pages/my-page.tsx`
2. Add route in `frontend/src/App.tsx`:
   ```tsx
   <Route path="my-page" element={<MyPage />} />
   ```
3. Add nav link in `frontend/src/components/layout/sidebar.tsx`

### Add a new permission

1. Add to the permission enum/logic in `backend/app/auth/permissions.py`
2. Include it in the default roles in `backend/app/routes/roles.py` (`_seed_default_roles`)
3. The `require_permission("my-feature:read")` dependency will be available immediately

### Add a new store (Zustand)

```typescript
// frontend/src/stores/myStore.ts
import { create } from 'zustand'
import { api } from '@/services/api'

interface MyState {
  items: string[]
  loadItems: () => Promise<void>
}

export const useMyStore = create<MyState>((set) => ({
  items: [],
  loadItems: async () => {
    const items = await api.get<string[]>('/api/my-feature/')
    set({ items })
  },
}))
```

---

## Linting & Formatting

```bash
# Python (ruff)
cd backend && ruff check app/
ruff check app/ --fix    # auto-fix

# TypeScript
cd frontend && npx tsc --noEmit

# Frontend lint
cd frontend && npx eslint .
```

---

## Debugging Tips

### Backend logs

```bash
# Tail in real-time
docker logs -f komajdon-api

# Local (no Docker)
tail -f /tmp/backend.log
```

### Add debug logging

```python
import logging
logger = logging.getLogger("komajdon")
logger.info("your message here")
# or: logger.warning, logger.error, logger.debug
```

Set `LOG_LEVEL=DEBUG` in `.env` for verbose output.

### Test an API endpoint with curl

```bash
# Sign in and capture token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/signin \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"Admin1234!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

# Use the token
curl -s http://localhost:8000/api/models/ \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# With project scope
curl -s http://localhost:8000/api/Product \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Project-Id: shop-website" | python3 -m json.tool
```

### Check rate limit headers

```bash
curl -sv http://localhost:8000/api/health 2>&1 | grep -i rate
# → X-RateLimit-Limit: 60
# → X-RateLimit-Remaining: 59
```

### Manual pipeline execution test

```bash
# Get pipeline ID
PID=$(curl -s http://localhost:8000/api/pipelines/ \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['_id'] if d else '')")

# Run it
curl -s -X POST "http://localhost:8000/api/pipelines/run/$PID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool
```

---

## Troubleshooting

### Backend won't start

```
ValueError: SECRET_KEY environment variable not set
```

**Fix:** Set `SECRET_KEY` in `.env` or export it:
```bash
export SECRET_KEY="your-secure-key"
```

### MongoDB connection refused

```
pymongo.errors.ServerSelectionTimeoutError: localhost:27017: [Errno 111] Connection refused
```

**Fix:** Start MongoDB:
```bash
docker run -d --name komajdon-db -p 27017:27017 mongo:7
```

### Frontend shows blank page

Check the browser console for errors. Common causes:
- Backend not running → API calls fail → ErrorBoundary catches
- Missing CORS origin → check `CORS_ORIGINS` in `.env`
- Build artifacts from old versions → try `rm -rf node_modules && npm install`

### CORS errors in browser

Add the frontend URL to `CORS_ORIGINS` in `.env`:
```
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5500
```

### "Model already exists" when creating in a project

Models names are unique per project. Delete the existing model first, or use a different name.

### Tests pass locally but fail in CI

Common causes:
- Missing env vars → ensure `SECRET_KEY=test` is set
- Different Python version → check `python --version`
- Different MongoDB version → check aggregation pipeline compatibility

---

## Architecture Notes

### Request lifecycle

```
Browser → Vite proxy → FastAPI → Middleware stack:
  1. SecurityHeadersMiddleware (adds security headers)
  2. AuditLogMiddleware (logs request to _audit_logs)
  3. RateLimitMiddleware (checks + decrements rate limit)
  4. CORS middleware
  ...
  5. Route handler (auth → permission check → business logic → response)
```

### Project isolation flow

```
1. User selects project in topbar dropdown
2. api.setProjectId() stores it → X-Project-Id header on all requests
3. Backend optional_project / require_project dependency resolves project
   - Lookup by: _id (string) → slug → _id (ObjectId)
4. check_project_access() verifies: admin? owner? member? → 403 if none
5. _project_collection() prefixes collection name: {project_id}__CollectionName
6. Data queries automatically scope to the prefixed collection
```

### Permission check order

```
1. Is endpoint auth-protected? (schema.auth_protected)
2. Is user authenticated? (require_user / optional_user)
3. Does user have required permission? (require_permission)
4. Is user the owner? (owner_id filter, admin bypass)
5. Does user have project access? (check_project_access)
```
