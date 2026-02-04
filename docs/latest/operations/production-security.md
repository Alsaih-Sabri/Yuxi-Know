# Production Security Guide

This guide covers security best practices for deploying Yuxi-Know in production.

## 🚨 Critical Security Steps

### 1. Secrets Management

**Never commit secrets to git!**

#### Generate Secure Secrets

```bash
# Linux/macOS
./scripts/generate-secrets.sh

# Windows PowerShell
.\scripts\generate-secrets.ps1
```

This creates:
- `docker/secrets/neo4j_password` - Neo4j database password
- `docker/secrets/admin_password` - Admin user password
- `docker/secrets/jwt_secret` - JWT token signing secret
- `docker/secrets/minio_access_key` - MinIO access key
- `docker/secrets/minio_secret_key` - MinIO secret key

#### Add API Keys

```bash
# Add your API keys to secret files
echo 'your-openai-key' > docker/secrets/openai_api_key
echo 'your-siliconflow-key' > docker/secrets/siliconflow_api_key
echo 'your-tavily-key' > docker/secrets/tavily_api_key
echo 'your-deepseek-key' > docker/secrets/deepseek_api_key
echo 'your-gemini-key' > docker/secrets/gemini_api_key
echo 'your-voyage-key' > docker/secrets/voyage_api_key

# Set proper permissions
chmod 600 docker/secrets/*
```

#### Rotate Exposed Secrets

If you've accidentally committed secrets to git:

1. **Rotate ALL exposed credentials immediately**
2. **Remove from git history:**

```bash
# Remove .env from git history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (CAREFUL!)
git push origin --force --all
```

3. **Update .gitignore** (already done)

### 2. SSL/TLS Configuration

#### Option A: Let's Encrypt (Recommended)

```bash
# Setup SSL certificate
./scripts/setup-ssl.sh yourdomain.com admin@yourdomain.com

# Update nginx configuration
# Edit docker/nginx/nginx-ssl.conf and replace 'yourdomain.com' with your domain

# Update docker-compose.prod.yml to use SSL config
```

#### Option B: Self-Signed Certificate (Development Only)

```bash
mkdir -p docker/volumes/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout docker/volumes/ssl/nginx-selfsigned.key \
  -out docker/volumes/ssl/nginx-selfsigned.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

### 3. Environment Configuration

```bash
# Copy template
cp .env.prod.template .env.prod

# Edit .env.prod with your settings
# IMPORTANT: Use secret files, not hardcoded values!
```

### 4. Security Scanning

Run security scan before deployment:

```bash
./scripts/security-scan.sh
```

This checks for:
- Docker image vulnerabilities
- Python dependency vulnerabilities
- Exposed secrets in code
- Default passwords
- File permissions

### 5. Deployment

```bash
# Deploy with security checks
./scripts/deploy-production-secure.sh
```

## Security Checklist

### Before Deployment

- [ ] Generated strong passwords for all services
- [ ] Added API keys to Docker secrets
- [ ] Configured SSL/TLS certificates
- [ ] Updated .env.prod with production settings
- [ ] Ran security scan (no critical issues)
- [ ] Verified .env is not in git
- [ ] Set proper file permissions (700 for directories, 600 for files)
- [ ] Updated default passwords in docker-compose files
- [ ] Configured firewall rules
- [ ] Set up backup procedures

### After Deployment

- [ ] Verified HTTPS is working
- [ ] Tested all API endpoints
- [ ] Checked health monitoring
- [ ] Verified logs are being collected
- [ ] Tested rate limiting
- [ ] Reviewed audit logs
- [ ] Documented incident response procedures
- [ ] Set up alerting

## Security Best Practices

### 1. Secrets Management

✅ **DO:**
- Use Docker secrets for sensitive data
- Rotate secrets every 90 days
- Use strong, random passwords (32+ characters)
- Store secrets in secure password manager
- Limit secret access to necessary services only

❌ **DON'T:**
- Commit secrets to git
- Use default passwords
- Share secrets via email/chat
- Hardcode secrets in code
- Use weak passwords

### 2. Network Security

✅ **DO:**
- Use HTTPS for all external traffic
- Implement rate limiting
- Use internal networks for backend services
- Configure firewall rules
- Only expose necessary ports

❌ **DON'T:**
- Expose database ports to internet
- Use HTTP in production
- Allow unlimited requests
- Trust all network traffic

### 3. Container Security

✅ **DO:**
- Run containers as non-root users
- Use read-only filesystems where possible
- Set resource limits
- Keep images updated
- Scan images for vulnerabilities

❌ **DON'T:**
- Run as root
- Use latest tag in production
- Grant unnecessary capabilities
- Ignore security updates

### 4. Access Control

✅ **DO:**
- Use strong authentication
- Implement role-based access control
- Enable audit logging
- Require MFA for admin accounts
- Regular access reviews

❌ **DON'T:**
- Use default admin credentials
- Share admin accounts
- Disable authentication
- Allow anonymous access

## Incident Response

### If Secrets Are Exposed

1. **Immediate Actions:**
   - Rotate ALL exposed credentials
   - Review access logs for unauthorized access
   - Enable additional logging
   - Notify stakeholders

2. **Investigation:**
   - Identify what was exposed
   - Determine exposure duration
   - Check for unauthorized access
   - Document findings

3. **Remediation:**
   - Remove secrets from git history
   - Update all affected systems
   - Implement additional controls
   - Update documentation

4. **Prevention:**
   - Review security procedures
   - Implement secret scanning
   - Train team on security
   - Regular security audits

### If System Is Compromised

1. **Isolate** affected systems
2. **Preserve** evidence
3. **Investigate** attack vector
4. **Remediate** vulnerabilities
5. **Restore** from backup if needed
6. **Document** incident
7. **Improve** security posture

## Monitoring & Alerting

### Key Metrics to Monitor

- Failed authentication attempts
- API error rates
- Resource usage (CPU, memory, disk)
- Network traffic patterns
- Database query performance
- SSL certificate expiration

### Set Up Alerts For

- Multiple failed login attempts
- Unusual API access patterns
- High error rates
- Resource exhaustion
- SSL certificate expiring soon
- Security scan failures

## Compliance

### Data Protection

- Encrypt data at rest
- Encrypt data in transit (TLS)
- Implement data retention policies
- Regular backups
- Secure backup storage

### Audit Logging

- Log all authentication events
- Log data access and modifications
- Log administrative actions
- Retain logs for required period
- Protect log integrity

## Regular Maintenance

### Daily

- Monitor health checks
- Review error logs
- Check resource usage

### Weekly

- Review security logs
- Check backup status
- Update dependencies

### Monthly

- Security scan
- Test disaster recovery
- Review access logs
- Update documentation

### Quarterly

- Rotate secrets
- Security audit
- Performance review
- Capacity planning

## Support

For security issues:
- Report vulnerabilities: [GitHub Security](https://github.com/xerrors/Yuxi-Know/security)
- Security questions: Create a private security advisory

## Resources

- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
