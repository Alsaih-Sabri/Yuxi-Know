# Production Deployment Setup Guide

This guide covers the steps to deploy Yuxi-Know in a production environment using `docker-compose.prod.yml`.

## Prerequisites

- Docker and Docker Compose installed
- Access to the deployment server
- Required API keys (see below)

## Quick Start

### 1. Create Production Environment File

Copy the template and configure your environment:

```bash
cp .env.prod.template .env.prod
```

### 2. Configure Required Variables

Edit `.env.prod` and set the following **required** variables:

```bash
# Required: Admin credentials
YUXI_SUPER_ADMIN_NAME=admin
YUXI_SUPER_ADMIN_PASSWORD=your_secure_password_here

# Required: API Keys
SILICONFLOW_API_KEY=your_siliconflow_api_key
TAVILY_API_KEY=your_tavily_api_key
```

### 3. Optional Configuration

Uncomment and configure these if you need to override defaults:

```bash
# Neo4j (defaults are provided in docker-compose.prod.yml)
NEO4J_URI=bolt://graph:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password

# Milvus (defaults are provided)
MILVUS_URI=http://milvus:19530
MILVUS_DB_NAME=default

# MinIO (defaults are provided)
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

### 4. Deploy

```bash
docker compose -f docker-compose.prod.yml up -d
```

## Service Profiles

The production compose file includes optional services under the `all` profile:

- `mineru-vllm-server`: OCR service (requires GPU)
- `mineru-api`: OCR API (requires GPU)
- `paddlex`: PaddleX OCR (requires GPU)

To start with all services:

```bash
docker compose -f docker-compose.prod.yml --profile all up -d
```

## Health Checks

All critical services have health checks configured. Monitor them with:

```bash
docker compose -f docker-compose.prod.yml ps
```

## Accessing the Application

- **Web UI**: http://your-server-ip:80
- **API**: http://your-server-ip:80/api

## Troubleshooting

### Missing .env.prod File

**Error**: `env file /path/to/.env.prod not found`

**Solution**: Ensure you've created `.env.prod` from `.env.prod.template` as described in step 1.

### Service Health Check Failures

Check logs for specific services:

```bash
docker compose -f docker-compose.prod.yml logs api
docker compose -f docker-compose.prod.yml logs milvus
```

### Port Conflicts

If port 80 is already in use, modify the web service port mapping in `docker-compose.prod.yml`:

```yaml
web:
  ports:
    - "8080:80"  # Change 80 to your preferred port
```

## Security Recommendations

1. **Change default passwords**: Update Neo4j, MinIO, and admin passwords
2. **Use strong credentials**: Generate secure passwords for all services
3. **Restrict network access**: Use firewall rules to limit access
4. **Enable HTTPS**: Configure reverse proxy (nginx/traefik) with SSL certificates
5. **Regular updates**: Keep Docker images and dependencies updated

## Data Persistence

The following directories contain persistent data:

- `./saves`: Application data
- `./docker/volumes/neo4j`: Graph database
- `./docker/volumes/milvus`: Vector database
- `./docker/volumes/paddlex`: PaddleX models

**Backup these directories regularly** to prevent data loss.

## Scaling Considerations

For production workloads:

1. **Resource Limits**: Add resource constraints in docker-compose.prod.yml
2. **External Databases**: Consider using managed Neo4j and Milvus services
3. **Load Balancing**: Deploy multiple API instances behind a load balancer
4. **Monitoring**: Implement logging and monitoring (Prometheus, Grafana)

## Support

For issues and questions:
- GitHub Issues: https://github.com/Alsaih-Sabri/Yuxi-Know/issues
- Documentation: Check the `docs/` directory
