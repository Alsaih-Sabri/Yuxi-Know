# Dokploy Deployment Guide

This guide covers deploying Yuxi-Know on Dokploy platform.

## Overview

Dokploy clones your GitHub repository but doesn't include gitignored files like `.env.prod`. This guide shows how to configure environment variables directly in Dokploy.

## Deployment Steps

### 1. Create Application in Dokploy

1. Log into your Dokploy dashboard
2. Create a new **Docker Compose** application
3. Connect your GitHub repository
4. Set the compose file to: `docker-compose.dokploy.yml`

### 2. Configure Environment Variables

In Dokploy's application settings, add the following environment variables:

#### Required Variables

```bash
# Admin Credentials (REQUIRED)
YUXI_SUPER_ADMIN_NAME=admin
YUXI_SUPER_ADMIN_PASSWORD=your_secure_password_here

# API Keys (REQUIRED)
SILICONFLOW_API_KEY=your_siliconflow_api_key
```

#### Optional API Keys

```bash
TAVILY_API_KEY=your_tavily_api_key
OPENAI_API_KEY=your_openai_key
OPENAI_API_BASE=https://api.openai.com/v1
GEMINI_API_KEY=your_gemini_key
ZHIPUAI_API_KEY=your_zhipuai_key
DASHSCOPE_API_KEY=your_dashscope_key
DEEPSEEK_API_KEY=your_deepseek_key
ARK_API_KEY=your_ark_key
TOGETHER_API_KEY=your_together_key
VOYAGE_API_KEY=your_voyage_key
```

#### Database Configuration (Optional - defaults provided)

```bash
# Neo4j
NEO4J_URI=bolt://graph:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=change_this_password

# Milvus
MILVUS_URI=http://milvus:19530
MILVUS_DB_NAME=default

# MinIO
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

#### OCR Services (Optional)

```bash
# MinerU Official API
MINERU_ACCESS_KEY_ID=your_mineru_key
MINERU_SECRET_ACCESS_KEY=your_mineru_secret

# Google Cloud Vision
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
# OR
GOOGLE_CREDENTIALS_JSON={"type":"service_account",...}
```

### 3. Deploy

Click **Deploy** in Dokploy. The deployment will:
1. Clone your repository
2. Build Docker images
3. Start all services
4. Run health checks

### 4. Access Your Application

Once deployed, access your application at:
- **Web UI**: `http://your-dokploy-domain`
- **API**: `http://your-dokploy-domain/api`

## Differences from docker-compose.prod.yml

The `docker-compose.dokploy.yml` file differs from `docker-compose.prod.yml`:

1. **No `env_file` directive**: All environment variables are passed directly through Dokploy
2. **All variables explicit**: Every required environment variable is listed in the `environment` section
3. **Default values**: Sensible defaults are provided using `${VAR:-default}` syntax

## Troubleshooting

### Build Failures

**Check build logs** in Dokploy dashboard:
- API build issues: Check Python dependencies in `pyproject.toml`
- Web build issues: Check Node.js dependencies in `web/package.json`

### Service Health Check Failures

Monitor service health in Dokploy:

```bash
# SSH into your Dokploy server
docker ps
docker logs api-prod
docker logs milvus
docker logs graph
```

### Missing Environment Variables

If you see errors about missing environment variables:
1. Go to Dokploy application settings
2. Add the missing variable
3. Redeploy the application

### Port Conflicts

If port 80 is already in use, modify the web service in `docker-compose.dokploy.yml`:

```yaml
web:
  ports:
    - "8080:80"  # Change to available port
```

## Security Best Practices

1. **Strong Passwords**: Use strong, unique passwords for:
   - `YUXI_SUPER_ADMIN_PASSWORD`
   - `NEO4J_PASSWORD`
   - `MINIO_SECRET_KEY`

2. **API Key Security**: Store API keys securely in Dokploy's environment variables (they're encrypted)

3. **Network Security**: Configure Dokploy's firewall rules to restrict access

4. **HTTPS**: Enable SSL/TLS in Dokploy settings for your domain

## Data Persistence

Dokploy automatically handles volume persistence for:
- `./saves` - Application data
- `./docker/volumes/neo4j` - Graph database
- `./docker/volumes/milvus` - Vector database
- `./docker/volumes/paddlex` - PaddleX models

**Backup Strategy**: Configure Dokploy's backup feature or manually backup these directories.

## Updating the Application

To update your deployment:

1. Push changes to your GitHub repository
2. In Dokploy, click **Redeploy**
3. Dokploy will pull latest changes and rebuild

## GPU Services (Optional)

The following services require GPU and are under the `all` profile:
- `mineru-vllm-server`
- `mineru-api`
- `paddlex`

To enable GPU services:
1. Ensure your Dokploy server has NVIDIA GPU
2. Install NVIDIA Container Toolkit
3. In Dokploy, enable the `all` profile in compose settings

## Monitoring

Monitor your application:
- **Dokploy Dashboard**: Real-time service status
- **Logs**: Access logs for each service
- **Metrics**: CPU, memory, and disk usage

## Support

For issues:
- **Dokploy Issues**: Check Dokploy documentation
- **Application Issues**: GitHub Issues at https://github.com/Alsaih-Sabri/Yuxi-Know/issues
- **Documentation**: See `docs/` directory

## Migration from docker-compose.prod.yml

If you were using `docker-compose.prod.yml`:

1. Export variables from your `.env.prod` file
2. Add them to Dokploy environment variables
3. Switch compose file to `docker-compose.dokploy.yml`
4. Redeploy

No data migration needed - volumes remain the same.
