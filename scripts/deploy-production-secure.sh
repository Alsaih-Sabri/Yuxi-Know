#!/bin/bash
set -e

echo "🚀 Secure Production Deployment"
echo "================================"

# Configuration
DOMAIN=${DOMAIN:-"yourdomain.com"}
ENV_FILE=".env.prod"
COMPOSE_FILE="docker-compose.prod.yml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Pre-deployment checks
echo "📋 Running pre-deployment checks..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ Do not run as root${NC}"
    exit 1
fi

# Check if .env.prod exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ $ENV_FILE not found${NC}"
    echo "📝 Copy .env.prod.template to .env.prod and configure"
    exit 1
fi

# Check if secrets directory exists
if [ ! -d "docker/secrets" ]; then
    echo -e "${RED}❌ docker/secrets directory not found${NC}"
    echo "📝 Run: ./scripts/generate-secrets.sh"
    exit 1
fi

# Check if required secrets exist
REQUIRED_SECRETS=(
    "docker/secrets/neo4j_password"
    "docker/secrets/admin_password"
    "docker/secrets/jwt_secret"
    "docker/secrets/minio_access_key"
    "docker/secrets/minio_secret_key"
)

for secret in "${REQUIRED_SECRETS[@]}"; do
    if [ ! -f "$secret" ]; then
        echo -e "${RED}❌ Required secret not found: $secret${NC}"
        echo "📝 Run: ./scripts/generate-secrets.sh"
        exit 1
    fi
done

# Check if SSL certificates exist (optional)
if [ ! -f "docker/volumes/certbot/conf/live/$DOMAIN/fullchain.pem" ]; then
    echo -e "${YELLOW}⚠️  SSL certificate not found for $DOMAIN${NC}"
    echo "📝 Run: ./scripts/setup-ssl.sh $DOMAIN your@email.com"
    read -p "Continue without SSL? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Backup current deployment
echo "💾 Creating backup..."
if [ -d "docker/volumes" ]; then
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    echo "Backing up volumes to $BACKUP_DIR..."
    cp -r docker/volumes "$BACKUP_DIR/" 2>/dev/null || true
    echo "✅ Backup created"
fi

# Pull latest code (optional, comment out if deploying from local changes)
# echo "📥 Pulling latest code..."
# git pull origin main

# Build images
echo "🔨 Building Docker images..."
docker compose -f $COMPOSE_FILE build --no-cache

# Run database migrations
echo "🗄️  Running database migrations..."
docker compose -f $COMPOSE_FILE run --rm api uv run python scripts/migrate_all.py || {
    echo -e "${YELLOW}⚠️  Migration warning (may be expected for fresh install)${NC}"
}

# Stop old containers
echo "🛑 Stopping old containers..."
docker compose -f $COMPOSE_FILE down

# Start new containers
echo "🚀 Starting new containers..."
docker compose -f $COMPOSE_FILE up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 30

# Health check
echo "🏥 Running health checks..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -k http://localhost/api/system/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Health check passed${NC}"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo -e "${RED}❌ Health check failed after $MAX_RETRIES attempts${NC}"
        echo "📋 Checking logs..."
        docker compose -f $COMPOSE_FILE logs --tail=50 api
        exit 1
    fi
    
    echo "⏳ Waiting... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

# Cleanup old images
echo "🧹 Cleaning up old images..."
docker image prune -f

# Display service status
echo ""
echo "📊 Service Status:"
docker compose -f $COMPOSE_FILE ps

echo ""
echo -e "${GREEN}✅ Deployment successful!${NC}"
echo "🌐 Application available at: http://localhost"
if [ -f "docker/volumes/certbot/conf/live/$DOMAIN/fullchain.pem" ]; then
    echo "🔒 HTTPS available at: https://$DOMAIN"
fi
echo ""
echo "📝 Next steps:"
echo "  - Monitor logs: docker compose -f $COMPOSE_FILE logs -f"
echo "  - Check metrics: http://localhost:9090 (if Prometheus enabled)"
echo "  - View dashboards: http://localhost:3000 (if Grafana enabled)"
