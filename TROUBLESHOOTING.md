# Troubleshooting Guide

## Port 80 Already Allocated Error

**Error:**
```
failed to set up container networking: Bind for 0.0.0.0:80 failed: port is already allocated
```

### On Ubuntu Server (Dokploy)

#### 1. Check What's Using Port 80

```bash
# Check what's using port 80
sudo lsof -i :80

# Or use netstat
sudo netstat -tulpn | grep :80

# Or use ss
sudo ss -tulpn | grep :80
```

#### 2. Common Causes & Solutions

**A. Apache/Nginx Running**
```bash
# Check if Apache is running
sudo systemctl status apache2

# Stop Apache
sudo systemctl stop apache2
sudo systemctl disable apache2

# Check if Nginx is running
sudo systemctl status nginx

# Stop Nginx
sudo systemctl stop nginx
sudo systemctl disable nginx
```

**B. Another Docker Container**
```bash
# List all running containers
docker ps

# Stop conflicting containers
docker stop <container-name>

# Or stop all containers
docker stop $(docker ps -q)
```

**C. Dokploy's Traefik/Proxy**

Dokploy uses Traefik as a reverse proxy. You should:

1. **Don't expose port 80 directly** - Let Dokploy/Traefik handle it
2. **Update docker-compose.dokploy.yml** to remove port mappings

#### 3. Fix for Dokploy Deployment

Update `docker-compose.dokploy.yml` to remove port mappings (Dokploy handles this):

```yaml
web:
  build:
    context: .
    dockerfile: docker/web.Dockerfile
    target: production
  image: yuxi-web:0.4.prod
  container_name: web-prod
  # Remove these lines for Dokploy:
  # ports:
  #   - "80:80"
  #   - "443:443"
  depends_on:
    - api
  networks:
    - app-network
  environment:
    - NODE_ENV=production
    - VITE_API_URL=http://api:5050
  command: nginx -g "daemon off;"
  restart: unless-stopped
```

Dokploy's Traefik will automatically route traffic to your container.

#### 4. Alternative: Use Different Ports

If you need to expose ports directly (not recommended for Dokploy):

```yaml
web:
  ports:
    - "8080:80"  # Use port 8080 instead
    - "8443:443"
```

Then access via: `http://your-server:8080`

### On Local Windows Machine

#### 1. Check What's Using Port 80

```powershell
# Check port 80
netstat -ano | findstr :80

# Find process ID and kill it
taskkill /PID <process-id> /F
```

#### 2. Stop Development Containers

```powershell
# Stop all containers
docker compose down

# Or stop specific compose file
docker compose -f docker-compose.dokploy.yml down
```

#### 3. Common Windows Conflicts

- **IIS (Internet Information Services)**
  - Open Services → Stop "World Wide Web Publishing Service"
  
- **Skype** (older versions)
  - Settings → Advanced → Connection → Uncheck "Use port 80 and 443"

- **SQL Server Reporting Services**
  - Uses port 80 by default

## Dokploy-Specific Issues

### Issue: Build Fails with pnpm Lockfile Error

**Solution:** Already fixed in `docker/web.Dockerfile` - uses `--no-frozen-lockfile`

### Issue: Environment Variables Not Set

**Solution:** Add all variables in Dokploy UI under "Environment Variables" section.

Required variables:
```bash
NEO4J_PASSWORD=<from-generate-secrets>
YUXI_SUPER_ADMIN_PASSWORD=<from-generate-secrets>
JWT_SECRET=<from-generate-secrets>
MINIO_ACCESS_KEY=<from-generate-secrets>
MINIO_SECRET_KEY=<from-generate-secrets>
OPENAI_API_KEY=<your-rotated-key>
SILICONFLOW_API_KEY=<your-rotated-key>
TAVILY_API_KEY=<your-rotated-key>
# ... etc
```

### Issue: SSL Certificate Not Working

**Solution:** Dokploy handles SSL automatically via Traefik + Let's Encrypt.

1. Add domain in Dokploy UI
2. Enable SSL toggle
3. Wait for certificate generation (1-2 minutes)
4. Verify HTTPS works

### Issue: Services Not Healthy

**Check logs:**
```bash
# In Dokploy UI, go to Logs tab
# Or via SSH:
docker logs <container-name>

# Check all services
docker compose -f docker-compose.dokploy.yml ps
```

**Common fixes:**
- Wait longer (Milvus takes ~3 minutes, Neo4j ~30s)
- Check environment variables are set
- Verify database passwords match
- Check network connectivity between services

### Issue: Milvus Unhealthy / Dependency Failed

**Error:** `dependency milvus failed to start: container milvus is unhealthy`

**Cause:** Milvus takes 2-3 minutes to fully start. Health check may timeout.

**Solutions:**

1. **Wait and check logs:**
```bash
# Check Milvus logs
docker logs milvus -f

# Check dependencies
docker logs milvus-etcd
docker logs milvus-minio

# Wait for "Milvus Proxy successfully started" message
```

2. **Increase timeouts** (already done in docker-compose.dokploy.yml):
   - `start_period: 180s` - Gives Milvus 3 minutes before health checks start
   - `retries: 10` - More retry attempts
   - `interval: 30s` - Check every 30 seconds

3. **Check dependencies are healthy:**
```bash
docker ps --filter "name=milvus"
# All should show "healthy" status
```

4. **Manual restart if stuck:**
```bash
# Restart just Milvus
docker compose -f docker-compose.dokploy.yml restart milvus

# Or restart all
docker compose -f docker-compose.dokploy.yml restart
```

5. **Clean start if corrupted:**
```bash
# Stop all
docker compose -f docker-compose.dokploy.yml down

# Remove Milvus data (WARNING: deletes data!)
rm -rf docker/volumes/milvus/milvus/*

# Start fresh
docker compose -f docker-compose.dokploy.yml up -d
```

## Network Issues

### Services Can't Connect to Each Other

**Cause:** Docker network not created or services on different networks.

**Solution:**
```bash
# Check networks
docker network ls

# Inspect network
docker network inspect yuxi-know_app-network

# Recreate network
docker compose -f docker-compose.dokploy.yml down
docker compose -f docker-compose.dokploy.yml up -d
```

### Can't Access from Outside

**For Dokploy:**
1. Check domain DNS points to server
2. Verify firewall allows ports 80/443
3. Check Dokploy domain configuration
4. Verify Traefik is routing correctly

**Check firewall:**
```bash
# Ubuntu/Debian
sudo ufw status
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check if ports are listening
sudo netstat -tulpn | grep -E ':(80|443)'
```

## Database Connection Issues

### Neo4j Connection Failed

**Check:**
```bash
# Verify Neo4j is running
docker logs graph

# Test connection
docker exec -it graph cypher-shell -u neo4j -p <password>
```

### Milvus Connection Failed

**Check:**
```bash
# Verify Milvus is healthy
docker logs milvus

# Check dependencies
docker logs milvus-etcd
docker logs milvus-minio
```

## Performance Issues

### Build Takes Too Long

**Solution:**
```bash
# Use BuildKit
export DOCKER_BUILDKIT=1

# Build with cache
docker compose -f docker-compose.dokploy.yml build --parallel

# Clean build cache if needed
docker builder prune
```

### Container Crashes / OOM

**Check resources:**
```bash
# Check container stats
docker stats

# Check system resources
free -h
df -h
```

**Increase resources** in Dokploy or docker-compose:
```yaml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

## Getting Help

1. **Check Logs:**
   - Dokploy UI → Logs tab
   - `docker logs <container-name>`
   - `docker compose -f docker-compose.dokploy.yml logs -f`

2. **Health Checks:**
   ```bash
   curl http://localhost/api/system/health
   docker compose -f docker-compose.dokploy.yml ps
   ```

3. **Debug Mode:**
   ```bash
   # Run with verbose output
   docker compose -f docker-compose.dokploy.yml up --verbose
   ```

4. **Reset Everything:**
   ```bash
   # Nuclear option - removes all data!
   docker compose -f docker-compose.dokploy.yml down -v
   docker system prune -a
   docker compose -f docker-compose.dokploy.yml up -d --build
   ```

## Quick Reference

**Start services:**
```bash
docker compose -f docker-compose.dokploy.yml up -d
```

**Stop services:**
```bash
docker compose -f docker-compose.dokploy.yml down
```

**View logs:**
```bash
docker compose -f docker-compose.dokploy.yml logs -f
```

**Restart service:**
```bash
docker compose -f docker-compose.dokploy.yml restart api
```

**Rebuild and restart:**
```bash
docker compose -f docker-compose.dokploy.yml up -d --build --force-recreate
```
