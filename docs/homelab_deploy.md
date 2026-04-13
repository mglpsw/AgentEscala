# Homelab Deployment Guide

This guide explains how to deploy AgentEscala to your homelab infrastructure.

## Prerequisites

### Homelab Requirements

1. **Docker Host**: Linux server with Docker and Docker Compose installed
2. **Traefik**: Reverse proxy with Let's Encrypt configured
3. **Traefik Network**: External Docker network named `traefik-public` (or configured name)
4. **Domain**: DNS record pointing to your homelab (e.g., `agentescala.yourdomain.com`)

### Verify Homelab Setup

```bash
# Check Traefik network exists
docker network inspect traefik-public

# Check Traefik is running
docker ps | grep traefik
```

## Deployment Steps

### 1. Clone Repository

On your homelab server:

```bash
git clone https://github.com/mglpsw/AgentEscala.git
cd AgentEscala
```

### 2. Configure Environment

```bash
# Copy example environment file
cp infra/.env.homelab.example infra/.env.homelab

# Edit configuration
nano infra/.env.homelab
```

**Required Configuration**:

```bash
# Database credentials (change these!)
POSTGRES_USER=agentescala
POSTGRES_PASSWORD=your-secure-password-here
POSTGRES_DB=agentescala

# Application secret (generate a random string)
SECRET_KEY=your-secret-key-minimum-32-characters

# Admin email
ADMIN_EMAIL=admin@yourdomain.com

# Homelab network (adjust if your Traefik network has a different name)
TRAEFIK_NETWORK=traefik-public

# Your domain
DOMAIN=agentescala.yourdomain.com
```

**Generate SECRET_KEY**:
```bash
# Python method
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL method
openssl rand -base64 32
```

### 3. Deploy

#### Option A: Using Deployment Script (Recommended)

```bash
# Build locally and deploy
./infra/scripts/couple_to_homelab.sh --build

# Or pull from registry (if available)
./infra/scripts/couple_to_homelab.sh
```

#### Option B: Manual Deployment

```bash
# Build image
docker build -t ghcr.io/mglpsw/agentescala:latest .

# Deploy with docker-compose
cd infra
docker-compose -f docker-compose.homelab.yml --env-file .env.homelab up -d
```

### 4. Verify Deployment

```bash
# Check containers are running
docker-compose -f infra/docker-compose.homelab.yml ps

# Check logs
docker-compose -f infra/docker-compose.homelab.yml logs -f

# Test health endpoint
curl https://agentescala.yourdomain.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-04-13T18:40:15.347Z",
  "version": "1.0.0"
}
```

### 5. Initialize Database

```bash
# Seed with sample data (optional)
docker-compose -f infra/docker-compose.homelab.yml exec backend python -m backend.seed
```

### 6. Access Application

- **API**: https://agentescala.yourdomain.com
- **API Docs**: https://agentescala.yourdomain.com/docs
- **Health**: https://agentescala.yourdomain.com/health

## Configuration Details

### Traefik Labels Explained

```yaml
# Enable Traefik for this container
- "traefik.enable=true"

# Specify which Docker network to use
- "traefik.docker.network=traefik-public"

# Routing rule (which domain to respond to)
- "traefik.http.routers.agentescala.rule=Host(`agentescala.yourdomain.com`)"

# Use HTTPS entrypoint
- "traefik.http.routers.agentescala.entrypoints=websecure"

# Enable TLS
- "traefik.http.routers.agentescala.tls=true"

# Use Let's Encrypt for certificate
- "traefik.http.routers.agentescala.tls.certresolver=letsencrypt"

# Backend port
- "traefik.http.services.agentescala.loadbalancer.server.port=8000"

# Health check configuration
- "traefik.http.services.agentescala.loadbalancer.healthcheck.path=/health"
- "traefik.http.services.agentescala.loadbalancer.healthcheck.interval=30s"
```

### Network Configuration

**Two Networks**:

1. **traefik-public** (external):
   - Connects Traefik to Backend
   - Allows external access

2. **agentescala_internal** (internal):
   - Connects Backend to Database
   - Isolated from external access
   - Database is not exposed

### Volume Configuration

**agentescala_postgres_data**:
- Persists database data
- Survives container restarts
- Located in Docker volumes directory
- Backup this volume for data safety

## Maintenance

### View Logs

```bash
# All logs
docker-compose -f infra/docker-compose.homelab.yml logs -f

# Backend only
docker-compose -f infra/docker-compose.homelab.yml logs -f backend

# Database only
docker-compose -f infra/docker-compose.homelab.yml logs -f db
```

### Restart Services

```bash
# Restart all
docker-compose -f infra/docker-compose.homelab.yml restart

# Restart backend only
docker-compose -f infra/docker-compose.homelab.yml restart backend
```

### Update Application

```bash
# Pull latest code
cd /path/to/AgentEscala
git pull

# Rebuild and restart
docker-compose -f infra/docker-compose.homelab.yml down
docker build -t ghcr.io/mglpsw/agentescala:latest .
docker-compose -f infra/docker-compose.homelab.yml up -d
```

### Backup Database

```bash
# Backup
docker-compose -f infra/docker-compose.homelab.yml exec db \
  pg_dump -U agentescala agentescala > backup_$(date +%Y%m%d).sql

# Restore
cat backup_20260413.sql | docker-compose -f infra/docker-compose.homelab.yml exec -T db \
  psql -U agentescala agentescala
```

### Stop Application

```bash
# Stop but keep data
docker-compose -f infra/docker-compose.homelab.yml down

# Stop and remove volumes (DELETES DATA!)
docker-compose -f infra/docker-compose.homelab.yml down -v
```

## Troubleshooting

### Issue: Traefik not routing to AgentEscala

**Check**:
1. Is the domain correct in `.env.homelab`?
2. Does DNS resolve to your homelab IP?
3. Is Traefik network correct?
4. Are labels correct in docker-compose?

```bash
# Check Traefik dashboard
https://traefik.yourdomain.com/dashboard/

# Check if container is on the right network
docker inspect agentescala_backend | grep Networks
```

### Issue: Database connection errors

**Check**:
1. Is DATABASE_URL correct in `.env.homelab`?
2. Is database container running?
3. Are credentials correct?

```bash
# Test database connection
docker-compose -f infra/docker-compose.homelab.yml exec backend \
  python -c "from backend.config.database import engine; print(engine.connect())"
```

### Issue: SSL certificate errors

**Check**:
1. Is domain accessible from internet? (Let's Encrypt needs this)
2. Is Traefik configured for Let's Encrypt?
3. Check Traefik logs for certificate errors

```bash
# Check Traefik logs
docker logs traefik | grep letsencrypt
```

### Issue: Backend won't start

**Check**:
1. View logs: `docker-compose -f infra/docker-compose.homelab.yml logs backend`
2. Is database healthy? `docker-compose -f infra/docker-compose.homelab.yml ps`
3. Are environment variables set correctly?

### Issue: Cannot access API

**Check**:
1. Health endpoint: `curl https://agentescala.yourdomain.com/health`
2. Container status: `docker-compose -f infra/docker-compose.homelab.yml ps`
3. Traefik routing: Check Traefik dashboard
4. Firewall: Is port 443 open?

## Monitoring

### Health Checks

Traefik automatically monitors the `/health` endpoint every 30 seconds.

### Manual Health Check

```bash
# Should return 200 and JSON with "status": "healthy"
curl -i https://agentescala.yourdomain.com/health
```

### Resource Usage

```bash
# Container stats
docker stats agentescala_backend agentescala_db
```

## Security Considerations

### Implemented
- ✅ SSL/TLS via Let's Encrypt
- ✅ Database on isolated network
- ✅ No direct database exposure
- ✅ Health check for monitoring
- ✅ Secure password storage (environment variables)

### Recommended Additional Security
- 🔲 Implement authentication (JWT)
- 🔲 Set up firewall rules
- 🔲 Configure rate limiting in Traefik
- 🔲 Regular security updates
- 🔲 Database backups
- 🔲 Log monitoring

## Integration with Homelab Observability

### Prometheus Metrics (Future)

Add to backend:
```yaml
labels:
  - "prometheus.io/scrape=true"
  - "prometheus.io/port=8000"
  - "prometheus.io/path=/metrics"
```

### Grafana Dashboard (Future)

Create dashboard with:
- Request rate
- Response time
- Error rate
- Database connections
- Shift counts
- Swap request status

### Loki Logging (Future)

Configure Docker logging driver to send logs to Loki.

## Next Steps

1. **Access API Documentation**: https://agentescala.yourdomain.com/docs
2. **Create Admin User**: Use seed script or API
3. **Create Agents**: Via API or future frontend
4. **Configure Monitoring**: Integrate with homelab observability
5. **Set Up Backups**: Automate database backups

## Support

If you encounter issues:

1. Check this guide's troubleshooting section
2. Review logs: `docker-compose logs -f`
3. Check project documentation in `/docs`
4. Open issue on GitHub: https://github.com/mglpsw/AgentEscala/issues
