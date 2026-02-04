#!/bin/bash
set -e

echo "🔐 Generating secure secrets..."

SECRETS_DIR="docker/secrets"
mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

# Generate secrets
echo "Generating Neo4j password..."
openssl rand -base64 32 > "$SECRETS_DIR/neo4j_password"

echo "Generating MinIO credentials..."
openssl rand -base64 32 > "$SECRETS_DIR/minio_access_key"
openssl rand -base64 32 > "$SECRETS_DIR/minio_secret_key"

echo "Generating admin password..."
openssl rand -base64 32 > "$SECRETS_DIR/admin_password"

echo "Generating JWT secret..."
openssl rand -hex 32 > "$SECRETS_DIR/jwt_secret"

# Set permissions
chmod 600 "$SECRETS_DIR"/*

echo "✅ Secrets generated in $SECRETS_DIR"
echo ""
echo "⚠️  IMPORTANT: Store these secrets securely!"
echo "📝 Add API keys manually:"
echo "   echo 'your-key' > $SECRETS_DIR/openai_api_key"
echo "   echo 'your-key' > $SECRETS_DIR/siliconflow_api_key"
echo "   echo 'your-key' > $SECRETS_DIR/tavily_api_key"
echo "   echo 'your-key' > $SECRETS_DIR/deepseek_api_key"
echo "   echo 'your-key' > $SECRETS_DIR/gemini_api_key"
echo "   echo 'your-key' > $SECRETS_DIR/voyage_api_key"
echo ""
echo "🔒 Generated passwords:"
echo "   Neo4j: $(cat $SECRETS_DIR/neo4j_password)"
echo "   Admin: $(cat $SECRETS_DIR/admin_password)"
echo "   MinIO Access: $(cat $SECRETS_DIR/minio_access_key)"
echo "   MinIO Secret: $(cat $SECRETS_DIR/minio_secret_key)"
echo ""
echo "⚠️  SAVE THESE PASSWORDS - They won't be shown again!"
