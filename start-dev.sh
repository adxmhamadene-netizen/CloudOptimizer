#!/usr/bin/env bash
set -e

echo "==> Starting CloudOptimizer dev environment"

# Backend
echo "  Starting FastAPI backend on :8000 ..."
PYTHONPATH=$(pwd) uvicorn backend.app.main:app \
  --reload \
  --port 8000 \
  --log-level info &
BACKEND_PID=$!

# Give backend a moment to start
sleep 2

# Frontend
echo "  Starting Next.js frontend on :3000 ..."
cd frontend && npm run dev &
FRONTEND_PID=$!

echo ""
echo "  Backend:  http://localhost:8000"
echo "  API docs: http://localhost:8000/docs"
echo "  Frontend: http://localhost:3000"
echo ""
echo "  Press Ctrl+C to stop both services."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
