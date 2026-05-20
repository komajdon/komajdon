# Komajdon Backend

FastAPI backend that powers the Komajdon BaaS platform — auto-generated REST APIs, auth, realtime, file storage, aggregation pipelines, and permission controls.

## Stack

- **Python 3.11+** / **FastAPI** / **Motor** (async MongoDB driver)
- **JWT** (python-jose) + **bcrypt** (passlib) for auth
- **WebSockets** for realtime broadcasting
- **GridFS** for file storage
- **Pydantic v2** for schema validation

## Directory Structure

```
backend/
├── app/
│   ├── main.py              # App entry, lifespan, route registration
│   ├── config.py             # Settings (env-based via pydantic-settings)
│   ├── database.py           # Motor connection manager
│   ├── cache.py              # In-memory TTL cache
│   ├── websocket.py          # WebSocket connection manager
│   ├── middleware.py          # Rate limiting, audit log, security headers
│   ├── exceptions.py         # Global exception handler
│   ├── auth/
│   │   ├── deps.py           # FastAPI dependencies (require_user, etc.)
│   │   ├── jwt.py            # JWT creation/verification + bcrypt
│   │   ├── permissions.py    # Permission checking engine
│   │   └── projects.py       # Project access control
│   ├── routes/
│   │   ├── auth.py           # Signup, signin, verify, reset, refresh
│   │   ├── models.py         # Model schema CRUD
│   │   ├── dynamic.py        # Dynamic CRUD engine (7 operations)
│   │   ├── pipelines.py      # Aggregation pipelines
│   │   ├── compositions.py   # API chaining
│   │   ├── files.py          # GridFS file storage
│   │   ├── discover.py       # Endpoint discovery
│   │   ├── roles.py          # Role/permission management
│   │   ├── api_keys.py       # API key management
│   │   ├── projects.py       # Project CRUD
│   │   ├── rate_limits.py    # Per-endpoint rate limit rules
│   │   ├── aggregations.py   # Aggregation templates
│   │   ├── realtime.py       # WebSocket endpoint
│   │   └── sdk.py            # SDK generation (TS + Python)
│   └── schemas/
│       ├── model_schema.py   # Model field definitions
│       ├── user.py           # User models
│       └── composition.py    # Composition models
├── shared/
│   └── stage_builders.py     # Shared pipeline stage builders
├── tests/                    # pytest test suite (async)
├── Dockerfile
├── Dockerfile.dev
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

## Setup

```bash
# Install
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt  # for development

# Configure
cp ../.env.example .env
# Edit .env and set SECRET_KEY to a secure random value

# Run
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | **Yes** | — | JWT signing key (generate with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`) |
| `MONGODB_URL` | No | `mongodb://localhost:27017` | MongoDB connection string |
| `DATABASE_NAME` | No | `komajdon` | Database name |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | JWT access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Refresh token TTL |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Comma-separated allowed origins |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## API Endpoints

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/signup` | Register |
| POST | `/api/auth/signin` | Login |
| POST | `/api/auth/refresh` | Refresh token |
| POST | `/api/auth/logout` | Invalidate refresh token |
| GET | `/api/auth/me` | Current user |
| POST | `/api/auth/verify-email` | Verify email (dev: token logged) |
| POST | `/api/auth/forgot-password` | Request reset |
| POST | `/api/auth/reset-password` | Reset password |
| GET | `/api/auth/users` | List users (admin) |
| PATCH | `/api/auth/users/{id}` | Update user (admin) |
| DELETE | `/api/auth/users/{id}` | Delete user (admin) |

### Models (Schema Management)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/models/` | List models |
| POST | `/api/models/` | Create model |
| GET | `/api/models/{name}` | Get model |
| PUT | `/api/models/{name}` | Update model |
| DELETE | `/api/models/{name}` | Delete model + drop collection |
| GET | `/api/models/{name}/export` | Export schema as JSON |
| POST | `/api/models/import` | Import schema from JSON |

### Dynamic CRUD (Auto-generated per model)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/{collection}` | List (filter, sort, paginate, search) |
| POST | `/api/{collection}` | Create |
| GET | `/api/{collection}/{id}` | Get by ID |
| PATCH | `/api/{collection}/{id}` | Partial update |
| PUT | `/api/{collection}/{id}` | Full replace |
| DELETE | `/api/{collection}/{id}` | Soft delete |
| POST | `/api/{collection}/{id}/restore` | Restore soft-deleted |
| POST | `/api/{collection}/bulk` | Bulk create/update/delete |

### Aggregation Pipelines
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/pipelines/` | List pipelines |
| POST | `/api/pipelines/` | Create pipeline |
| GET | `/api/pipelines/{id}` | Get pipeline |
| PUT | `/api/pipelines/{id}` | Update pipeline |
| DELETE | `/api/pipelines/{id}` | Delete pipeline |
| POST | `/api/pipelines/run/{id}` | Execute pipeline |
| POST | `/api/pipelines/{id}/expose` | Expose as REST endpoint |

### File Storage (GridFS)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/storage/upload/{collection}` | Upload file |
| GET | `/api/storage/download/{file_id}` | Download file |
| GET | `/api/storage/list/{collection}` | List files |
| DELETE | `/api/storage/delete/{file_id}` | Delete file |

### Permissions & Roles
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/roles/` | List roles |
| POST | `/api/roles/` | Create custom role |
| DELETE | `/api/roles/{name}` | Delete role |

### Projects
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/projects/` | List projects |
| POST | `/api/projects/` | Create project |
| PUT | `/api/projects/{id}` | Update project |
| DELETE | `/api/projects/{id}` | Delete project |

### Other
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/discover/` | List all available endpoints |
| GET | `/api/health` | Health check |
| GET | `/api/keys/` | List API keys |
| POST | `/api/keys/` | Create API key |
| DELETE | `/api/keys/{id}` | Delete API key |
| GET | `/api/rate-limits/` | List rate limit rules |
| POST | `/api/rate-limits/` | Create rate limit rule |
| PUT | `/api/rate-limits/{id}` | Update rule |
| DELETE | `/api/rate-limits/{id}` | Delete rule |

## Testing

```bash
cd backend
python -m pytest tests/ -v --tb=short
python -m pytest tests/ -v --cov=app  # with coverage
```

## Docker

```bash
docker build -t komajdon-backend .
docker run -p 8000:8000 -e SECRET_KEY=your-key komajdon-backend
```

## License

MIT. See [../docs/LICENSE](../docs/LICENSE).
