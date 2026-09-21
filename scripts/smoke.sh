#!/bin/sh
set -eu
base_url="${1:-http://localhost:8080}"
curl --fail --silent "$base_url/health/live" >/dev/null
curl --fail --silent "$base_url/health/ready" >/dev/null
curl --fail --silent "$base_url/" | grep -q "UniFlow"
echo "UniFlow smoke test passed"

