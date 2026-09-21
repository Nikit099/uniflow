#!/bin/sh
set -eu
alembic upgrade head
if [ "${DEMO_SEED:-true}" = "true" ]; then
  python -m app.seed_cli
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

