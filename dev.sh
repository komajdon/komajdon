#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

cleanup() {
  echo -e "\n${YELLOW}Shutting down...${NC}"
  kill $BACKEND_PID 2>/dev/null || true
  kill $FRONTEND_PID 2>/dev/null || true
  echo -e "${GREEN}Done.${NC}"
  exit 0
}
trap cleanup SIGINT SIGTERM

echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        Komajdon Dev Mode 🚀         ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
echo ""

# ─── Check SECRET_KEY ────────────────────────────────
if [ -z "$SECRET_KEY" ]; then
  if [ -f "$ROOT_DIR/.env" ]; then
    export $(grep -v '^#' "$ROOT_DIR/.env" | xargs)
  elif [ -f "$BACKEND_DIR/.env" ]; then
    export $(grep -v '^#' "$BACKEND_DIR/.env" | xargs)
  fi
fi
if [ -z "$SECRET_KEY" ]; then
  echo -e "${YELLOW}SECRET_KEY not set. Generating one...${NC}"
  export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
  echo -e "${GREEN}✓ SECRET_KEY generated (set it in .env to persist)${NC}"
fi

# ─── Check Python deps ───────────────────────────────
setup_backend() {
  cd "$BACKEND_DIR"
  local missing=0
  for mod in fastapi motor uvicorn jose passlib; do
    python3 -c "import $mod" 2>/dev/null || { missing=1; break; }
  done
  if [ $missing -eq 0 ]; then
    echo -e "${GREEN}✓ Backend deps found${NC}"
    return 0
  fi
  echo -e "${YELLOW}Installing backend deps...${NC}"
  pip install -r requirements.txt -q 2>/dev/null && {
    echo -e "${GREEN}✓ Backend deps installed${NC}"
    return 0
  }
  pip install --break-system-packages -r requirements.txt -q 2>/dev/null && {
    echo -e "${GREEN}✓ Backend deps installed (break-system-packages)${NC}"
    return 0
  }
  echo -e "${RED}✗ Failed to install backend deps. Try: cd backend && pip install -r requirements.txt${NC}"
  return 1
}

# ─── MongoDB ──────────────────────────────────────────
if command -v mongosh &>/dev/null || command -v mongod &>/dev/null; then
  echo -e "${GREEN}✓ MongoDB detected locally${NC}"
elif command -v docker &>/dev/null && docker info &>/dev/null; then
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -q komajdon-db; then
    echo -e "${GREEN}✓ MongoDB already running in Docker${NC}"
  else
    echo -e "${CYAN}Starting MongoDB via Docker...${NC}"
    docker run -d --name komajdon-db -p 27017:27017 mongo:7 2>/dev/null || \
      docker start komajdon-db 2>/dev/null || true
    echo -e "${GREEN}✓ MongoDB started${NC}"
  fi
else
  echo -e "${YELLOW}⚠ No MongoDB found. Start one: docker run -d -p 27017:27017 mongo:7${NC}"
fi
echo ""

# ─── Backend ──────────────────────────────────────────
cd "$ROOT_DIR"
if setup_backend; then
  cd "$BACKEND_DIR"
  SECRET_KEY="$SECRET_KEY" uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
  BACKEND_PID=$!
  echo -e "${GREEN}✓ Backend running on http://localhost:8000${NC}"
else
  echo -e "${YELLOW}⚠ Backend not started${NC}"
fi

# ─── Frontend ─────────────────────────────────────────
if [ -d "$FRONTEND_DIR/node_modules" ]; then
  cd "$FRONTEND_DIR"
  npm run dev &
  FRONTEND_PID=$!
  echo -e "${GREEN}✓ Frontend running on http://localhost:5173${NC}"
else
  echo -e "${YELLOW}Installing frontend deps...${NC}"
  cd "$FRONTEND_DIR"
  npm install && npm run dev &
  FRONTEND_PID=$!
  echo -e "${GREEN}✓ Frontend running on http://localhost:5173${NC}"
fi
echo ""

# ─── Ready ────────────────────────────────────────────
echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     Komajdon Dev Mode 🚀            ║${NC}"
echo -e "${CYAN}║                                      ║${NC}"
echo -e "${CYAN}║  Backend:  http://localhost:8000      ║${NC}"
echo -e "${CYAN}║  API Docs: http://localhost:8000/docs ║${NC}"
echo -e "${CYAN}║  Frontend: http://localhost:5173      ║${NC}"
echo -e "${CYAN}║                                      ║${NC}"
echo -e "${CYAN}║  Press Ctrl+C to stop                 ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
echo ""

wait
