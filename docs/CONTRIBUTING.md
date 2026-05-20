# Contributing to Komajdon

Thank you for your interest! We welcome contributions of all kinds.

## Code of Conduct

Be respectful, constructive, and inclusive. Harassment or discriminatory behavior will not be tolerated.

## How to Contribute

### Report Bugs
Open an issue with:
- A clear title and description
- Steps to reproduce
- Expected vs actual behavior
- Screenshots or logs if relevant

### Suggest Features
Open an issue with:
- Use case / problem you're solving
- Proposed solution outline
- Any prior art or references

### Submit Code

1. **Fork** the repo
2. **Create a branch**: `git checkout -b feature/your-feature`
3. **Make changes** following the existing code style
4. **Run tests**:
   ```bash
   cd backend && python -m pytest tests/ -v
   cd frontend && npm test
   ```
5. **Lint**:
   ```bash
   cd backend && ruff check app/
   cd frontend && npx tsc --noEmit
   ```
6. **Commit** with a descriptive message
7. **Push** and open a Pull Request

### Pull Request Guidelines

- Keep PRs focused on a single concern
- Add tests for new functionality
- Update README or docs if behavior changes
- Ensure all CI checks pass
- Reference any related issues

## Development Setup

```bash
# Backend
cp .env.example backend/.env
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## Project Structure

```
komajdon/
├── backend/          # FastAPI Python backend
│   ├── app/          # Application code
│   │   ├── auth/     # Auth (JWT, bcrypt, dependencies)
│   │   ├── routes/   # Route handlers
│   │   └── schemas/  # Pydantic schemas
│   ├── shared/       # Shared utilities
│   └── tests/        # Test suite
├── frontend/         # React + Vite + TypeScript
│   ├── src/
│   │   ├── pages/    # Route pages
│   │   ├── components/  # UI components
│   │   ├── stores/   # Zustand stores
│   │   └── services/ # API + WebSocket clients
│   └── ...
└── docs/             # Documentation
```

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
