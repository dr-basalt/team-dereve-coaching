#!/bin/bash
set -e
cd "$(dirname "$0")/.."
git pull
docker compose build
docker compose up -d
echo "Deployed successfully!"
docker compose ps
