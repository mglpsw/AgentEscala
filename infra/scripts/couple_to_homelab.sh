#!/bin/bash
set -e

# AgentEscala Homelab Coupling Script
# This script deploys AgentEscala to your homelab infrastructure

echo "=== AgentEscala Homelab Deployment ==="
echo ""

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$INFRA_DIR")"
ENV_FILE="$INFRA_DIR/.env.homelab"
COMPOSE_FILE="$INFRA_DIR/docker-compose.homelab.yml"

# Check if .env.homelab exists
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env.homelab not found!"
    echo "Please copy .env.homelab.example to .env.homelab and configure it."
    exit 1
fi

# Load environment variables
source "$ENV_FILE"

echo "Configuration loaded:"
echo "  - Domain: $DOMAIN"
echo "  - Traefik Network: $TRAEFIK_NETWORK"
echo "  - Database: $POSTGRES_DB"
echo ""

# Verify Traefik network exists
if ! docker network inspect "$TRAEFIK_NETWORK" >/dev/null 2>&1; then
    echo "Error: Traefik network '$TRAEFIK_NETWORK' does not exist!"
    echo "Please create it first or check your homelab setup."
    exit 1
fi

# Build or pull image
echo "Building/pulling AgentEscala image..."
if [ "$1" == "--build" ]; then
    echo "Building local image..."
    docker build -t ghcr.io/mglpsw/agentescala:latest "$PROJECT_ROOT"
else
    echo "Pulling image from registry..."
    docker pull ghcr.io/mglpsw/agentescala:latest || {
        echo "Warning: Could not pull image. Building locally instead..."
        docker build -t ghcr.io/mglpsw/agentescala:latest "$PROJECT_ROOT"
    }
fi

# Deploy with docker-compose
echo ""
echo "Deploying AgentEscala..."
cd "$INFRA_DIR"
docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "AgentEscala is now running!"
echo "  - URL: https://$DOMAIN"
echo "  - Health check: https://$DOMAIN/health"
echo ""
echo "To view logs:"
echo "  docker-compose -f $COMPOSE_FILE logs -f"
echo ""
echo "To stop:"
echo "  docker-compose -f $COMPOSE_FILE down"
echo ""
