# Komajdon

**Visual Backends for MongoDB — Just Point & Click.**

Komajdon is a Backend-as-a-Service platform that abstracts backend complexity and provides instant MongoDB-backed APIs. Design data models visually and get auto-generated REST APIs with auth, real-time, file storage, and permission controls — without writing backend code.

## Architecture

```
komajdon/
├── backend/                  # FastAPI (Python) backend [→](backend/README.md)
│   ├── app/
│   │   ├── main.py           # App entry point
│   │   ├── config.py         # Settings (env-based)
│   │   ├── database.py       # Motor (async MongoDB) connection
│   │   ├── cache.py          # In-memory TTL cache
│   │   ├── websocket.py      # WebSocket connection manager
│   │   ├── exceptions.py     # Global exception handler
│   │   ├── middleware.py      # Rate limiting + audit + security headers
│   │   ├── auth/             # JWT auth + bcrypt + permissions
│   │   ├── routes/           # All API route handlers
│   │   └── schemas/          # Pydantic models
│   ├── shared/               # Shared utilities
│   ├── tests/                # pytest suite (async)
│   ├── Dockerfile            # Production container
│   └── pyproject.toml        # Python project config
├── frontend/                 # React / Vite / TypeScript [→](frontend/README.md)
│   ├── src/
│   │   ├── pages/            # Route pages
│   │   ├── components/       # Reusable UI components
│   │   ├── services/         # API + WebSocket clients
│   │   ├── stores/           # Zustand state management
│   │   └── hooks/            # Custom React hooks
│   ├── Dockerfile            # Production container (nginx)
│   └── nginx.conf            # Production reverse proxy
├── docs/                     # Documentation [→](docs/)
│   ├── CONTRIBUTING.md       # Contribution guidelines
│   ├── DEVELOPMENT.md        # Development workflows & troubleshooting
│   └── LICENSE               # MIT license
├── docker-compose.yml        # Dev environment
├── docker-compose.prod.yml   # Production environment
└── Makefile                  # Common commands
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local dev without Docker)

### Setup

```bash
# Clone and enter
cd komajdon

# Generate a secure secret key and add it to .env
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Edit .env and set SECRET_KEY to the generated value

# Start everything
make dev
```

This starts:
- **MongoDB** on `localhost:27017`
- **Backend** (FastAPI) on `localhost:8000`
- **Frontend** (Vite) on `localhost:5173`

### Local Development (without Docker)

```bash
# Backend
cp .env.example backend/.env
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## API Overview

| Endpoint | Description |
|----------|-------------|
| `POST /api/auth/register` | Register a new user |
| `POST /api/auth/login` | Login |
| `GET /api/auth/me` | Current user info |
| `GET /api/discover` | List all available endpoints |
| `GET /api/models` | List data models |
| `POST /api/models` | Create a new data model |
| `GET /api/{collection}` | List documents (with filtering/sorting) |
| `POST /api/{collection}` | Create a document |
| `GET /api/{collection}/:id` | Get a document by ID |
| `PATCH /api/{collection}/:id` | Update a document |
| `DELETE /api/{collection}/:id` | Soft-delete a document |
| `GET /ws/{collection}` | WebSocket for realtime updates |
| `GET /api/health` | Health check |

### Query Parameters

- `filter=field__op=value` — Filter with operators: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `nin`, `regex`, `contains`
- `sort=field,-field` — Sort ascending/descending
- `limit=N` — Page size (max 1000)
- `skip=N` — Pagination offset
- `fields=name,status` — Field projection
- `populate=relationName` — Populate relationships

## Testing

```bash
# Run backend tests
make test

# Or manually:
cd backend
pip install -r requirements-dev.txt
python -m pytest tests/ -v --cov=app
```

## Production Deployment

```bash
# Build and start production containers
cp .env.example .env
# Edit .env with secure values
make docker-up-prod
```

The production stack uses:
- **MongoDB** — with health checks and persistent volumes
- **Backend** — Python 3.12 slim with non-root user, health checks
- **Frontend** — Nginx serving static build with API proxy

## Security

- **SECRET_KEY** is required (no default) — generates error if missing
- Passwords hashed with bcrypt via passlib
- Password complexity validation (min length, uppercase, lowercase, digit)
- Rate limiting on all endpoints (stricter on auth)
- JWT validation on all protected endpoints
- Owner-based row-level security
- CORS origins configurable via environment variable

## Project Status

| Category | Status |
|----------|--------|
| Authentication | Core working (register/login/JWT) |
| Auto-Generated APIs | Comprehensive CRUD (7 operations) |
| Realtime Engine | WebSocket broadcasting |
| Admin Dashboard | Feature-rich React UI |
| File Storage | GridFS-based |
| Aggregation Pipelines | Pipeline builder + expose API |
| API Compositions | Step-based API chaining |
| SDK Generation | TypeScript + Python |
| Security | Hardened (no defaults, rate limiting, validation) |

## License

MIT — see [docs/LICENSE](docs/LICENSE) for the full text.

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines on reporting bugs, suggesting features, and submitting pull requests.

## Component Docs

- [Backend README](backend/README.md) — API reference, environment variables, architecture
- [Frontend README](frontend/README.md) — Pages, components, build commands, design decisions
- [Development Guide](docs/DEVELOPMENT.md) — Quick start, workflows, testing, debugging, troubleshooting
