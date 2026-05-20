# Komajdon Frontend

React + Vite + TypeScript admin dashboard for the Komajdon BaaS platform. Visual model builder, data explorer, aggregation pipelines, API composer, and more.

## Stack

- **React 18** / **Vite 6** / **TypeScript** (strict mode)
- **TailwindCSS** with custom dark theme
- **Zustand** for state management
- **React Router v6** for routing
- **Framer Motion** for animations
- **Lucide React** for icons

## Directory Structure

```
frontend/
├── src/
│   ├── main.tsx               # App entry
│   ├── App.tsx                # Router + auth guard
│   ├── index.css              # Global styles, Tailwind
│   ├── pages/
│   │   ├── login.tsx          # Auth (signin/signup)
│   │   ├── dashboard.tsx      # Model grid
│   │   ├── model-builder.tsx  # Visual model designer
│   │   ├── model-detail.tsx   # 5-tab detail view
│   │   ├── data-explorer.tsx  # Document table browser
│   │   ├── aggregations.tsx   # Pipeline management
│   │   ├── api-composer.tsx   # API chaining UI
│   │   ├── projects.tsx       # Project management
│   │   ├── users.tsx          # User management
│   │   ├── roles.tsx          # Role/permission editor
│   │   ├── api-keys.tsx       # API key management
│   │   ├── storage.tsx        # File upload/download
│   │   ├── settings.tsx       # App settings
│   │   └── rate-limits.tsx    # Per-endpoint rate limits
│   ├── components/
│   │   ├── layout/
│   │   │   ├── dashboard-layout.tsx  # Main layout shell
│   │   │   ├── sidebar.tsx           # Navigation sidebar
│   │   │   └── topbar.tsx            # Top bar + project selector
│   │   └── ui/                # Reusable UI primitives
│   │       ├── button.tsx
│   │       ├── input.tsx
│   │       ├── badge.tsx
│   │       ├── modal.tsx
│   │       ├── json-editor.tsx
│   │       └── ...
│   ├── stores/                # Zustand state stores
│   │   ├── authStore.ts
│   │   ├── modelStore.ts
│   │   ├── projectStore.ts
│   │   └── uiStore.ts
│   ├── services/
│   │   ├── api.ts             # HTTP client (fetch-based)
│   │   └── socket.ts          # WebSocket client
│   ├── hooks/
│   │   └── useRealtime.ts     # Real-time data hook
│   ├── lib/
│   │   └── utils.ts           # Helper functions
│   └── types/
│       └── index.ts           # TypeScript interfaces
├── public/                    # Static assets
├── Dockerfile                 # Production (nginx)
├── Dockerfile.dev
├── nginx.conf                 # API proxy config
├── vite.config.ts             # Dev proxy, path aliases
├── tailwind.config.js         # Custom theme
├── tsconfig.json
└── package.json
```

## Setup

```bash
cd frontend
npm install
npm run dev
```

Starts on `http://localhost:5173` with API proxy to `http://localhost:8000`.

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server (hot reload) |
| `npm run build` | TypeScript check + production build |
| `npm run preview` | Preview production build |
| `npm test` | Run vitest suite |
| `npm run lint` | Run ESLint |

## Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | Model grid with create/import |
| `/login` | Login | Auth (signin/signup tabs) |
| `/models/new` | Model Builder | Visual schema designer |
| `/models/:name` | Model Detail | Schema, Playground, Aggregations, SDK, Realtime tabs |
| `/models/:name/edit` | Model Builder | Edit existing model |
| `/data` | Data Explorer | Browse, filter, paginate documents |
| `/aggregations` | Aggregations | Pipeline CRUD + run |
| `/composer` | API Composer | Step-based API chaining |
| `/projects` | Projects | Multi-project management |
| `/users` | Users | User management (admin) |
| `/roles` | Roles | Role/permission editor |
| `/keys` | API Keys | API key management |
| `/storage` | File Storage | Upload/download files |
| `/rate-limits` | Rate Limits | Per-endpoint rate limit rules |
| `/settings` | Settings | App configuration |

## Project Selector

The topbar includes a project dropdown. Selecting a project scopes all API requests via the `X-Project-Id` header — models, pipelines, and data queries return only that project's resources.

## Key Design Decisions

- **No React Query / SWR** — Zustand stores call `api.get()` directly
- **Native `fetch`** — no Axios dependency
- **Dark theme only** — custom Tailwind config with slate/mongodb-green palette
- **JSONEditor** — lightweight textarea-based JSON editor (no Monaco)
- **Project isolation** — `X-Project-Id` header on every request via `api.ts`

## Docker

```bash
# Production build
docker build -t komajdon-frontend .
docker run -p 5173:80 komajdon-frontend

# Dev build (hot reload)
docker build -f Dockerfile.dev -t komajdon-frontend-dev .
```

## License

MIT. See [../docs/LICENSE](../docs/LICENSE).
