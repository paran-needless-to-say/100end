#!/bin/bash

# Simple Docker Run Script for 100end Backend (Single Container)
# This script runs only the backend container, assuming risk-scoring service is external

set -e

echo "=================================================="
echo "  100end Backend - Simple Docker Run"
echo "=================================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please copy .env.example to .env and configure it"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Build the Docker image
echo ""
echo "Building Docker image..."
docker build -t 100end-backend:latest .

# Stop and remove existing container if it exists
echo ""
echo "Removing existing container (if any)..."
docker rm -f 100end-backend 2>/dev/null || true

# Run the container with environment variables from host
echo ""
echo "Starting container..."
docker run -d \
  --name 100end-backend \
  --restart unless-stopped \
  -p 8888:8888 \
  -e ETHERSCAN_API_KEY="${ETHERSCAN_API_KEY}" \
  -e ALCHEMY_API_KEY="${ALCHEMY_API_KEY}" \
  -e DUNE_API_KEY="${DUNE_API_KEY}" \
  -e DB_HOST="${DB_HOST}" \
  -e DB_USER="${DB_USER}" \
  -e DB_PASSWORD="${DB_PASSWORD}" \
  -e DB_NAME="${DB_NAME}" \
  -e FLASK_ENV="${FLASK_ENV}" \
  -e SECRET_KEY="${SECRET_KEY}" \
  -e RISK_SCORING_API_URL="${RISK_SCORING_API_URL}" \
  -e PYTHONUNBUFFERED=1 \
  100end-backend:latest

# Wait a moment for the container to start
echo ""
echo "Waiting for container to start..."
sleep 5

# Check if container is running
if docker ps | grep -q 100end-backend; then
    echo ""
    echo "✓ Container is running!"
    echo ""
    echo "Container logs:"
    docker logs --tail=20 100end-backend
    echo ""
    echo "=================================================="
    echo "Backend API: http://localhost:8888"
    echo "=================================================="
    echo ""
    echo "Commands:"
    echo "  View logs:    docker logs -f 100end-backend"
    echo "  Stop:         docker stop 100end-backend"
    echo "  Restart:      docker restart 100end-backend"
    echo "  Remove:       docker rm -f 100end-backend"
else
    echo ""
    echo "ERROR: Container failed to start!"
    echo "Check logs with: docker logs 100end-backend"
    exit 1
fi
