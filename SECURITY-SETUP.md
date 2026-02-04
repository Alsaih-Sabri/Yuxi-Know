# 🔒 Security Setup Guide

**CRITICAL: Follow these steps before deploying to production!**

## ⚠️ Your Current Security Issues

I've detected the following security issues in your repository:

1. **Exposed API Keys in `.env` file:**
   - OpenAI API key
   - SiliconFlow API key
   - Tavily API key
   - DeepSeek API key
   - Gemini API key
   - Voyage API key
   - MinerU credentials
   - Admin password

2. **Default passwords in docker-compose files:**
   - Neo4j: `0123456789`
   - MinIO: `minioadmin`

## 🚨 Immediate Actions Required

### Step 1: Rotate ALL Exposed API Keys (DO THIS FIRST!)

Go to each provider and generate new API keys:

- [ ] OpenAI: https://platform.openai.com/api-keys
- [ ] SiliconFlow: https://cloud.siliconflow.cn/
- [ ] Tavily: https://app.tavily.com/
- [ ] DeepSeek: https://platform.deepseek.com/
- [ ] Google Gemini: https://aistudio.google.com/apikey
- [ ] Voyage AI: https://dash.voyageai.com/
- [ ] MinerU: https://mineru.net/

### Step 2: Generate Secure Secrets

**On Windows (PowerShell):**
```powershell
.\scripts\generate-secrets.ps1
```

**On Linux/macOS:**
```bash
chmod +x scripts/generate-secrets.sh
./scripts/generate-secrets.sh
```

This will create `docker/secrets/` directory with secure passwords.

### Step 3: Add Your New API Keys

```bash
# Windows PowerShell
echo 'your-new-openai-key' | Out-File -FilePath 'docker\secrets\openai_api_key' -NoNewline
echo 'your-new-siliconflow-key' | Out-File -FilePath 'docker\secrets\siliconflow_api_key' -NoNewline
echo 'your-new-tavily-key' | Out-File -FilePath 'docker\secrets\tavily_api_key' -NoNewline
echo 'your-new-deepseek-key' | Out-File -FilePath 'docker\secrets\deepseek_api_key' -NoNewline
echo 'your-new-gemini-key' | Out-File -FilePath 'docker\secrets\gemini_api_key' -NoNewline
echo 'your-new-voyage-key' | Out-File -FilePath 'docker\secrets\voyage_api_key' -NoNewline

# Linux/macOS
echo 'your-new-openai-key' > docker/secrets/openai_api_key
echo 'your-new-siliconflow-key' > docker/secrets/siliconflow_api_key
echo 'your-new-tavily-key' > docker/secrets/tavily_api_key
echo 'your-new-deepseek-key' > docker/secrets/deepseek_api_key
echo 'your-new-gemini-key' > docker/secrets/gemini_api_key
echo 'your-new-voyage-key' > docker/secrets/voyage_api_key

# Set permissions (Linux/macOS only)
chmod 600 docker/secrets/*
```

### Step 4: Remove .env from Git History

**IMPORTANT: This will rewrite git history!**

```bash
# Backup first
cp .env .env.backup

# Remove from git history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (coordinate with team first!)
git push origin --force --all
```

### Step 5: Configure Production Environment

```bash
# Copy template
cp .env.prod.template .env.prod

# Edit .env.prod with your domain and settings
# DO NOT add API keys here - they're in docker/secrets/
```

### Step 6: Setup SSL (Production Only)

**If deploying to a server with a domain:**

```bash
# Linux/macOS
chmod +x scripts/setup-ssl.sh
./scripts/setup-ssl.sh yourdomain.com admin@yourdomain.com

# Update nginx config
# Edit docker/nginx/nginx-ssl.conf and replace 'yourdomain.com' with your domain
```

### Step 7: Run Security Scan

```bash
# Linux/macOS
chmod +x scripts/security-scan.sh
./scripts/security-scan.sh

# Windows - install WSL or use Docker
docker run --rm -v ${PWD}:/src trufflesecurity/trufflehog:latest filesystem /src
```

### Step 8: Deploy

```bash
# Linux/macOS
chmod +x scripts/deploy-production-secure.sh
./scripts/deploy-production-secure.sh

# Windows - use Docker Compose directly
docker compose -f docker-compose.prod.yml up -d --build
```

## 📋 Security Checklist

### Before Deployment

- [ ] Rotated all exposed API keys
- [ ] Generated secure passwords with scripts
- [ ] Added new API keys to docker/secrets/
- [ ] Removed .env from git history
- [ ] Created .env.prod from template
- [ ] Set up SSL certificates (production)
- [ ] Ran security scan (no critical issues)
- [ ] Verified .env is in .gitignore
- [ ] Set proper file permissions on secrets
- [ ] Updated docker-compose.prod.yml (if needed)
- [ ] Configured firewall rules
- [ ] Set up backup procedures

### After Deployment

- [ ] Verified HTTPS is working
- [ ] Tested login with new admin password
- [ ] Checked all services are healthy
- [ ] Verified API keys are working
- [ ] Tested file upload
- [ ] Checked logs for errors
- [ ] Set up monitoring alerts
- [ ] Documented admin credentials securely

## 🔐 What's Been Implemented

### 1. Secrets Management
- ✅ Docker secrets support
- ✅ Secret generation scripts (Windows + Linux)
- ✅ Secret reading utility (`src/utils/secrets.py`)
- ✅ .gitignore updated to prevent secret commits

### 2. SSL/TLS
- ✅ Nginx SSL configuration
- ✅ Let's Encrypt setup script
- ✅ Security headers (HSTS, CSP, etc.)
- ✅ HTTP to HTTPS redirect

### 3. Scripts
- ✅ `generate-secrets.sh/ps1` - Generate secure passwords
- ✅ `setup-ssl.sh` - Configure SSL certificates
- ✅ `deploy-production-secure.sh` - Secure deployment
- ✅ `security-scan.sh` - Security vulnerability scanning

### 4. Documentation
- ✅ Production security guide
- ✅ .env.prod.template with secure defaults
- ✅ This setup guide

## 🆘 Need Help?

### Common Issues

**Q: "Permission denied" when running scripts**
```bash
chmod +x scripts/*.sh
```

**Q: "Docker secrets not working"**
- Make sure files exist in `docker/secrets/`
- Check file permissions: `ls -la docker/secrets/`
- Verify docker-compose.prod.yml has secrets configured

**Q: "SSL certificate failed"**
- Ensure domain DNS points to your server
- Check port 80 is accessible from internet
- Verify email address is valid

**Q: "Health check failing"**
```bash
# Check logs
docker compose -f docker-compose.prod.yml logs api

# Check if services are running
docker compose -f docker-compose.prod.yml ps

# Restart services
docker compose -f docker-compose.prod.yml restart
```

## 📚 Additional Resources

- [Production Security Guide](docs/latest/operations/production-security.md)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

## ⚠️ Important Notes

1. **Never commit secrets to git** - Always use Docker secrets or environment variables
2. **Rotate secrets regularly** - Every 90 days minimum
3. **Use strong passwords** - 32+ characters, random
4. **Enable HTTPS in production** - Never use HTTP for sensitive data
5. **Monitor security logs** - Set up alerts for suspicious activity
6. **Keep dependencies updated** - Regular security updates
7. **Backup regularly** - Test restore procedures

## 🎯 Next Steps

After completing this setup:

1. Review [Production Security Guide](docs/latest/operations/production-security.md)
2. Set up monitoring and alerting
3. Configure automated backups
4. Document your deployment procedures
5. Train team on security best practices
6. Schedule regular security audits

---

**Remember: Security is not a one-time task, it's an ongoing process!**
