#!/bin/bash

# Docker Deployment Script for 100end Backend
# This script builds and deploys the application using Docker Compose

set -e  # Exit on error

echo "=================================================="
echo "  100end Backend Docker Deployment Script"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_error ".env file not found!"
    print_info "Please copy .env.example to .env and configure it:"
    print_info "  cp .env.example .env"
    print_info "  nano .env"
    exit 1
fi

print_info "Found .env file ✓"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed!"
    exit 1
fi

print_info "Docker is installed ✓"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed!"
    exit 1
fi

print_info "Docker Compose is installed ✓"

# Load environment variables to validate
print_info "Validating environment variables..."
source .env

REQUIRED_VARS=(
    "ETHERSCAN_API_KEY"
    "DB_HOST"
    "DB_USER"
    "DB_PASSWORD"
    "DB_NAME"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ] || [ "${!var}" = "your_${var,,}_here" ] || [[ "${!var}" == *"your_"* ]]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    print_error "The following required environment variables are not set or have placeholder values:"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    print_info "Please update your .env file with actual values"
    exit 1
fi

print_info "All required environment variables are set ✓"

# Stop and remove existing containers
print_info "Stopping existing containers..."
if docker compose version &> /dev/null; then
    docker compose down
else
    docker-compose down
fi

# Build images
print_info "Building Docker images..."
if docker compose version &> /dev/null; then
    docker compose build --no-cache
else
    docker-compose build --no-cache
fi

# Start services
print_info "Starting services..."
if docker compose version &> /dev/null; then
    docker compose up -d
else
    docker-compose up -d
fi

# Wait for services to be healthy
print_info "Waiting for services to be healthy..."
sleep 10

# Check service health
print_info "Checking service health..."

BACKEND_HEALTHY=false
RISK_SCORING_HEALTHY=false

for i in {1..30}; do
    if docker inspect 100end-backend | grep -q '"Health".*"healthy"'; then
        BACKEND_HEALTHY=true
    fi

    if docker inspect 100end-risk-scoring | grep -q '"Health".*"healthy"'; then
        RISK_SCORING_HEALTHY=true
    fi

    if $BACKEND_HEALTHY && $RISK_SCORING_HEALTHY; then
        break
    fi

    echo -n "."
    sleep 2
done

echo ""

if $BACKEND_HEALTHY; then
    print_info "Backend service is healthy ✓"
else
    print_warning "Backend service health check failed"
fi

if $RISK_SCORING_HEALTHY; then
    print_info "Risk-scoring service is healthy ✓"
else
    print_warning "Risk-scoring service health check failed"
fi

# Show running containers
echo ""
print_info "Running containers:"
if docker compose version &> /dev/null; then
    docker compose ps
else
    docker-compose ps
fi

# Show logs
echo ""
print_info "Recent logs:"
if docker compose version &> /dev/null; then
    docker compose logs --tail=20
else
    docker-compose logs --tail=20
fi

echo ""
echo "=================================================="
print_info "Deployment complete!"
echo "=================================================="
echo ""
print_info "Backend API: http://localhost:8888"
print_info "Risk Scoring API: http://localhost:5001"
echo ""
print_info "To view logs:"
echo "  docker compose logs -f backend"
echo "  docker compose logs -f risk-scoring"
echo ""
print_info "To stop services:"
echo "  docker compose down"
echo ""
