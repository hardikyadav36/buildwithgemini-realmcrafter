#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# Activate local virtualenv if present
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

export AGENT_ENGINE_RESOURCE_NAME="projects/701107460665/locations/us-central1/reasoningEngines/7269029975779442688"
export AGENT_DIRECTORY="app"
export PORT=8080

echo "Starting RealmCrafter frontend proxy..."
echo "AGENT_ENGINE_RESOURCE_NAME: $AGENT_ENGINE_RESOURCE_NAME"
echo "AGENT_DIRECTORY: $AGENT_DIRECTORY"
echo "URL: http://localhost:8080"

python main.py
