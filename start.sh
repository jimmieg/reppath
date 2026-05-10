#!/bin/bash

# Get the directory where this script lives
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

# Activate venv
source "$REPO_ROOT/venv/bin/activate"

# Start frontend in background (cd is scoped to subshell)
(cd "$REPO_ROOT/frontend" && npm run dev) &
FRONTEND_PID=$!

# Start backend from repo root so 'backend' module is found
cd "$REPO_ROOT"
python -m uvicorn backend.main:app --reload

# On Ctrl+C, kill frontend too
kill $FRONTEND_PID