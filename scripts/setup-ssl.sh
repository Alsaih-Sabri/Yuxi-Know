#!/bin/bash
set -e

DOMAIN=${1:-yourdomain.com}
EMAIL=${2:-admin@yourdomain.com}

echo "🔐 Setting up SSL certificate for $DOMAIN"
echo "=========================================="

# Validate inputs
if [ "$DOMAIN" = "yourdomain.com" ]; then
    echo "❌ Error: Please provide your actual domain name"
    echo "Usage: ./setup-ssl.sh yourdomain.com admin@yourdomain.com"
    exit 1
fi

# Create directories
echo "📁 Creating directories..."
mkdir -p docker/volumes/certbot/conf
mkdir -p docker/volumes/certbot/www

# Check if docker compose is running
if ! docker compose -f docker-compose.prod.yml ps | grep -q "web"; then
    echo "⚠️  Web container not running. Starting temporarily..."
    docker compose -f docker-compose.prod.yml up -d web
    sleep 5
fi

# Get certificate
echo "📜 Requesting SSL certificate from Let's Encrypt..."
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d $DOMAIN \
    -d www.$DOMAIN

if [ $? -eq 0 ]; then
    echo "✅ SSL certificate obtained successfully!"
    echo ""
    echo "📝 Next steps:"
    echo "1. Update docker/nginx/nginx-ssl.conf:"
    echo "   - Replace 'yourdomain.com' with '$DOMAIN'"
    echo "2. Update docker-compose.prod.yml to use nginx-ssl.conf"
    echo "3. Restart services: docker compose -f docker-compose.prod.yml restart web"
else
    echo "❌ Failed to obtain SSL certificate"
    echo "Please check:"
    echo "  - Domain DNS is pointing to this server"
    echo "  - Port 80 is accessible from internet"
    echo "  - Email address is valid"
    exit 1
fi
