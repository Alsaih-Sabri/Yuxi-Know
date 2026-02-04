#!/bin/bash
set -e

echo "🔍 Running security scans..."
echo "============================"

FAILED=0

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running"
    exit 1
fi

# Scan Docker images for vulnerabilities
echo ""
echo "📦 Scanning Docker images with Trivy..."
echo "----------------------------------------"

if docker images | grep -q "yuxi-api"; then
    echo "Scanning yuxi-api:0.4.prod..."
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
        aquasec/trivy image --severity HIGH,CRITICAL yuxi-api:0.4.prod || FAILED=1
else
    echo "⚠️  yuxi-api image not found, skipping..."
fi

if docker images | grep -q "yuxi-web"; then
    echo "Scanning yuxi-web:0.4.prod..."
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
        aquasec/trivy image --severity HIGH,CRITICAL yuxi-web:0.4.prod || FAILED=1
else
    echo "⚠️  yuxi-web image not found, skipping..."
fi

# Scan Python dependencies
echo ""
echo "🐍 Scanning Python dependencies..."
echo "-----------------------------------"
if [ -f "pyproject.toml" ]; then
    # Check if safety is installed
    if command -v safety &> /dev/null; then
        safety check --json || FAILED=1
    else
        echo "⚠️  'safety' not installed. Install with: pip install safety"
        echo "Skipping Python dependency scan..."
    fi
else
    echo "⚠️  pyproject.toml not found, skipping..."
fi

# Scan for secrets in code
echo ""
echo "🔐 Scanning for exposed secrets..."
echo "-----------------------------------"
if command -v trufflehog &> /dev/null; then
    trufflehog filesystem . --json --no-update || FAILED=1
else
    echo "⚠️  'trufflehog' not installed"
    echo "Install with: docker pull trufflesecurity/trufflehog:latest"
    echo "Or: brew install trufflehog (macOS)"
    echo "Skipping secret scan..."
fi

# Check for exposed .env files
echo ""
echo "📄 Checking for exposed .env files..."
echo "--------------------------------------"
if [ -f ".env" ]; then
    echo "⚠️  WARNING: .env file exists in root directory"
    echo "   Make sure it's in .gitignore and not committed to git"
    FAILED=1
fi

if git ls-files | grep -q "^\.env$"; then
    echo "❌ CRITICAL: .env file is tracked by git!"
    echo "   Run: git rm --cached .env"
    echo "   Then: git commit -m 'Remove .env from git'"
    FAILED=1
fi

# Check for default passwords
echo ""
echo "🔑 Checking for default passwords..."
echo "------------------------------------"
if grep -r "0123456789" docker-compose*.yml > /dev/null 2>&1; then
    echo "⚠️  WARNING: Default Neo4j password found in docker-compose files"
    echo "   Update to use Docker secrets"
    FAILED=1
fi

if grep -r "minioadmin" docker-compose*.yml > /dev/null 2>&1; then
    echo "⚠️  WARNING: Default MinIO credentials found in docker-compose files"
    echo "   Update to use Docker secrets"
    FAILED=1
fi

# Check file permissions
echo ""
echo "🔒 Checking file permissions..."
echo "--------------------------------"
if [ -d "docker/secrets" ]; then
    PERMS=$(stat -c %a docker/secrets 2>/dev/null || stat -f %A docker/secrets 2>/dev/null)
    if [ "$PERMS" != "700" ]; then
        echo "⚠️  WARNING: docker/secrets has permissions $PERMS (should be 700)"
        echo "   Run: chmod 700 docker/secrets"
        FAILED=1
    fi
    
    # Check individual secret files
    for file in docker/secrets/*; do
        if [ -f "$file" ]; then
            PERMS=$(stat -c %a "$file" 2>/dev/null || stat -f %A "$file" 2>/dev/null)
            if [ "$PERMS" != "600" ]; then
                echo "⚠️  WARNING: $file has permissions $PERMS (should be 600)"
                echo "   Run: chmod 600 $file"
                FAILED=1
            fi
        fi
    done
fi

# Summary
echo ""
echo "============================"
if [ $FAILED -eq 0 ]; then
    echo "✅ Security scan completed successfully"
    exit 0
else
    echo "⚠️  Security scan completed with warnings/errors"
    echo "Please review the issues above and fix them before deploying"
    exit 1
fi
