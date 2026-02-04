# 🚀 Dokploy Deployment Guide

Quick guide for deploying Yuxi-Know on Dokploy.

## Prerequisites

- Dokploy instance running
- Domain name pointing to your server (lightrag.webget.co.uk)
- Rotated API keys (see SECURITY-SETUP.md)

## Deployment Steps

### 1. Create New Application in Dokploy

1. Go to your Dokploy dashboard
2. Click "Create Application"
3. Choose "Docker Compose"
4. Connect your GitHub repository

### 2. Configure Environment Variables

In Dokploy's Environment Variables section, add these (use the passwords from `.\scripts\generate-secrets.ps1` output):

```bash
# Domain Configuration
DOMAIN=lightrag.webget.co.uk
ALLOWED_HOSTS=lightrag.webget.co.uk,www.lightrag.webget.co.uk

# Database Passwords (from generate-secrets.ps1 output)
NEO4J_PASSWORD=l3VaFTU07De0Y0DKWo/Ol4iWOuG6HCIHh0nYvRE4Qyw=
YUXI_SUPER_ADMIN_NAME=admin
YUXI_SUPER_ADMIN_PASSWORD=gC3uv95mu9xJ41OxbXj7dUOLhm6+aJFYWTFF+zC/Eqs=
JWT_SECRET=<your-jwt-secret-from-generate-secrets>
MINIO_ACCESS_KEY=LNhHCi/PHPng4XVQGHVCYx7blMOwLueW/2Yg8lRbwzo=
MINIO_SECRET_KEY=kDXZaq7/N+2Tvk5EEqxCo9KQAeBWGor4Ofvw5ZvxQtk=

# API Keys (USE YOUR NEW ROTATED KEYS!)
OPENAI_API_KEY=sk-proj-YOUR-NEW-KEY
SILICONFLOW_API_KEY=sk-YOUR-NEW-KEY
TAVILY_API_KEY=tvly-YOUR-NEW-KEY
DEEPSEEK_API_KEY=sk-YOUR-NEW-KEY
GEMINI_API_KEY=AIza-YOUR-NEW-KEY
VOYAGE_API_KEY=pa-YOUR-NEW-KEY

# Database URLs
NEO4J_URI=bolt://graph:7687
NEO4J_USERNAME=neo4j
MILVUS_URI=http://milvus:19530
MILVUS_DB_NAME=default
MINIO_URI=http://milvus-minio:9000

# Application Settings
ENVIRONMENT=production
RUNNING_IN_DOCKER=true
MODEL_DIR_IN_DOCKER=/models
```

### 3. Select Docker Compose File

In Dokploy settings:
- **Compose File**: `docker-compose.dokploy.yml` (or `docker-compose.prod.yml`)
- **Build Context**: `.`

### 4. Configure Domain & SSL

In Dokploy's domain settings:
1. Add domain: `lightrag.webget.co.uk`
2. Enable SSL (Dokploy handles Let's Encrypt automatically)
3. Enable HTTPS redirect

### 5. Deploy

1. Click "Deploy"
2. Wait for build to complete
3. Check logs for any errors
4. Visit https://lightrag.webget.co.uk

## Verification

After deployment:

```bash
# Check health
curl https://lightrag.webget.co.uk/api/system/health

# Should return: {"status":"ok","message":"服务正常运行"}
```

## Dokploy vs Docker Secrets

| Feature | Docker Secrets | Dokploy Env Vars |
|---------|---------------|------------------|
| **Setup** | Manual file creation | UI-based |
| **Security** | File-based, encrypted | Platform-managed |
| **Updates** | Requires container restart | Restart via UI |
| **Best For** | Self-hosted Docker | Managed platforms |

**For Dokploy**: Use environment variables (simpler, platform-native)  
**For self-hosted**: Use Docker secrets (more secure, file-based)

## Troubleshooting

### Services Not Starting

Check Dokploy logs:
```bash
# In Dokploy UI, go to Logs tab
# Look for errors in api, graph, milvus services
```

### Database Connection Errors

Verify environment variables are set correctly in Dokploy UI.

### SSL Issues

Dokploy handles SSL automatically. If issues:
1. Verify domain DNS points to server
2. Check Dokploy SSL settings
3. Ensure ports 80 and 443 are open

## Important Notes

1. **Don't use Docker secrets with Dokploy** - Use environment variables instead
2. **Rotate API keys** before adding to Dokploy
3. **Save passwords** from `generate-secrets.ps1` output
4. **Dokploy handles SSL** - No need for manual Let's Encrypt setup
5. **Persistent volumes** - Dokploy manages volume persistence automatically

## Security Checklist for Dokploy

- [ ] Rotated all API keys
- [ ] Generated secure passwords with `generate-secrets.ps1`
- [ ] Added all environment variables in Dokploy UI
- [ ] Enabled SSL in Dokploy
- [ ] Verified HTTPS redirect works
- [ ] Tested health endpoint
- [ ] Checked all services are running
- [ ] Verified admin login works

## Next Steps

After successful deployment:

1. Test all features
2. Set up monitoring (Dokploy has built-in monitoring)
3. Configure backups
4. Review logs regularly
5. Update dependencies periodically

---

**Need help?** Check Dokploy documentation or create an issue on GitHub.
