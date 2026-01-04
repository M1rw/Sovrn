# SOVRN Deployment Guide

This guide covers deploying SOVRN on a VPS for production use.

## Requirements

### Minimum VPS Specifications
- **CPU**: 4 vCPUs (AMD EPYC or Intel Xeon recommended)
- **RAM**: 8GB (16GB recommended for larger models)
- **Storage**: 40GB SSD
- **OS**: Ubuntu 22.04 LTS or Debian 12

### Recommended Providers
- **Hetzner Cloud**: CX31 (~€8/month) - Best value
- **Contabo**: VPS S SSD (~$7/month) - Budget option
- **DigitalOcean**: Basic Droplet (~$12/month)
- **Vultr**: High Frequency (~$12/month)

## Quick Deploy

### 1. Initial Server Setup

```bash
# Connect to your VPS
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose
apt install docker-compose-plugin -y

# Add your user to docker group (if not root)
usermod -aG docker $USER
```

### 2. Clone and Configure

```bash
# Clone repository
git clone https://github.com/yourusername/sovrn.git
cd sovrn

# Copy environment file
cp .env.example .env

# Generate secrets
echo "JWT_SECRET=$(openssl rand -hex 32)" >> .env
echo "DATABASE_URL=postgresql://sovrn:$(openssl rand -hex 16)@db:5432/sovrn" >> .env

# Edit configuration
nano .env
```

### 3. Download Model

```bash
# Make script executable
chmod +x scripts/download-model.sh

# Download the model (~7GB)
./scripts/download-model.sh
```

### 4. Start Services

```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### 5. Configure Domain (Optional)

Edit `infra/caddy/Caddyfile`:

```caddyfile
your-domain.com {
    reverse_proxy web:3000
    
    handle /api/* {
        reverse_proxy api:8000
    }
}
```

Restart Caddy:
```bash
docker compose restart caddy
```

## Production Checklist

### Security

- [ ] Change default database password
- [ ] Set strong JWT_SECRET
- [ ] Configure firewall (UFW)
- [ ] Enable automatic security updates
- [ ] Set up SSH key authentication
- [ ] Disable root login

```bash
# Configure UFW firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80
ufw allow 443
ufw enable
```

### Performance

- [ ] Enable swap (for low-memory systems)
- [ ] Configure resource limits in docker-compose.yml
- [ ] Set up log rotation

```bash
# Add 4GB swap
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### Monitoring

- [ ] Set up health check endpoint monitoring
- [ ] Configure log aggregation
- [ ] Set up disk space alerts

### Backups

- [ ] Configure database backups
- [ ] Set up automated backup schedule

```bash
# Manual database backup
docker compose exec db pg_dump -U sovrn sovrn > backup_$(date +%Y%m%d).sql

# Automated daily backups (add to crontab)
0 3 * * * cd /path/to/sovrn && docker compose exec -T db pg_dump -U sovrn sovrn > /backups/sovrn_$(date +\%Y\%m\%d).sql
```

## Updating

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker compose build
docker compose up -d

# Run migrations (if any)
docker compose exec api alembic upgrade head
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker compose logs api
docker compose logs infer

# Verify model file exists
ls -la models/

# Check disk space
df -h
```

### Out of Memory

```bash
# Check memory usage
free -h
docker stats

# Reduce inference memory limit in docker-compose.yml
# Or use a smaller model quantization
```

### Slow Response Times

```bash
# Check CPU usage
htop

# Increase inference threads in docker-compose.yml
# Or upgrade to a larger VPS
```

### Database Connection Issues

```bash
# Check database status
docker compose exec db pg_isready

# Reset database (WARNING: destroys data)
docker compose down -v
docker compose up -d
```

## Cost Breakdown

### Monthly Costs (Self-Hosted)

| Item | Cost |
|------|------|
| VPS (Hetzner CX31) | ~€8 |
| Domain (optional) | ~€1 |
| **Total** | **~€9/month** |

### Comparison with Cloud AI APIs

Generating 100 websites/month:
- **SOVRN (self-hosted)**: €9/month (unlimited)
- **OpenAI API**: ~$50-100/month
- **Anthropic API**: ~$60-120/month
- **Cloud SaaS**: $50-500/month

**Savings**: 80-95% cost reduction with SOVRN

## Support

- Documentation: `/docs`
- Issues: GitHub Issues
- Community: Discord Server
