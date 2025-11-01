# Production Deployment Guide - AWS EC2

Complete guide for deploying the Dynamic Business Landing Page Generator to AWS EC2 with Docker.

## Prerequisites

- AWS EC2 instance (Ubuntu 22.04 LTS)
- Minimum: t3.medium (2 vCPU, 4 GB RAM)
- Recommended: t3.large (2 vCPU, 8 GB RAM)
- 30+ GB storage
- Public IP address
- Security group with ports 22 (SSH) and 3000 (HTTP) open

## Step 1: Prepare EC2 Instance

### SSH into your instance

```bash
ssh -i your-key.pem ubuntu@your-ec2-public-ip
```

### Update system

```bash
sudo apt update && sudo apt upgrade -y
```

### Install Docker

```bash
# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up the stable repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add your user to docker group
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
exit
```

SSH back in and verify:

```bash
docker --version
docker compose version
```

## Step 2: Deploy Application

### Clone repository

```bash
cd /srv
sudo mkdir -p app
sudo chown $USER:$USER app
cd app
git clone <your-repo-url> .
```

### Configure environment

```bash
# Generate API key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Create production .env
sudo cp .env.production.example /srv/app/.env
sudo nano /srv/app/.env
```

Edit `/srv/app/.env` with your actual values:
- `API_KEY` - Generated key from above
- `OPENAI_API_KEY` - Your OpenAI API key
- `GOOGLE_MAPS_API_KEY` - Your Google Maps API key
- `FRONTEND_URL` - `http://YOUR_EC2_PUBLIC_IP:3000`
- `UNSPLASH_ACCESS_KEY` - (Optional) Your Unsplash key

### Make deployment script executable

```bash
chmod +x deploy.sh
```

### Deploy

```bash
./deploy.sh
```

This will:
1. Build all Docker images
2. Stop existing containers
3. Clean up old images
4. Start services
5. Verify health

## Step 3: Verify Deployment

### Check service status

```bash
docker compose ps
```

All services should show "healthy" status.

### Check logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f frontend
docker compose logs -f backend
docker compose logs -f agents
docker compose logs -f mcp
```

### Test health endpoints

```bash
# Frontend (accessible from browser)
curl http://localhost:3000

# Backend (internal only)
docker exec landing-backend curl http://localhost:8000/health

# Agents (internal only)
docker exec landing-agents curl http://localhost:8002/health

# MCP (internal only)
docker exec landing-mcp curl http://localhost:8003/health
```

### Access application

Open browser: `http://YOUR_EC2_PUBLIC_IP:3000`

## Step 4: Configure Security Group

In AWS Console → EC2 → Security Groups:

**Inbound Rules**:
- SSH (22) - Your IP only
- Custom TCP (3000) - 0.0.0.0/0 (or restrict to your IPs)

**Outbound Rules**:
- All traffic - 0.0.0.0/0 (for API calls to OpenAI, Google, etc.)

## Management Commands

### View running containers

```bash
docker compose ps
```

### Restart services

```bash
docker compose restart
```

### Stop services

```bash
docker compose down
```

### Update application

```bash
cd /srv/app
git pull
./deploy.sh
```

### View resource usage

```bash
docker stats
```

### Clean up (remove all containers and images)

```bash
docker compose down
docker system prune -a
```

## Monitoring

### Check disk usage

```bash
df -h
du -sh /srv/app/backend/artifacts
```

### Monitor logs

```bash
# Follow all logs
docker compose logs -f

# Last 100 lines
docker compose logs --tail=100

# Specific time range
docker compose logs --since 1h
```

### Backup artifacts

```bash
tar -czf artifacts-backup-$(date +%Y%m%d).tar.gz /srv/app/backend/artifacts
```

## Troubleshooting

### Service won't start

```bash
# Check logs for errors
docker compose logs [service_name]

# Verify .env file exists and has correct permissions
ls -la /srv/app/.env

# Rebuild specific service
docker compose build [service_name]
docker compose up -d [service_name]
```

### Out of memory

```bash
# Check memory usage
free -h
docker stats

# Restart services to free memory
docker compose restart
```

### Out of disk space

```bash
# Clean up Docker
docker system prune -a
docker volume prune

# Clean up old artifacts
find /srv/app/backend/artifacts -type d -mtime +7 -exec rm -rf {} +
```

### Network issues

```bash
# Verify network exists
docker network ls

# Recreate networks
docker compose down
docker compose up -d
```

### API key errors

```bash
# Verify .env file
cat /srv/app/.env | grep API_KEY

# Restart services to reload env
docker compose restart
```

## Scaling Considerations

### Increase worker processes

Edit `docker-compose.yml` and change `--workers` flag:

```yaml
command: uvicorn landing_api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Limit resource usage

Add resource limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '1'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 1G
```

## Security Best Practices

1. **Restrict SSH access** - Security group SSH only from your IP
2. **Use HTTPS** - Set up reverse proxy with SSL (Caddy/Nginx + Let's Encrypt)
3. **Rotate API keys** - Regular rotation of `API_KEY`
4. **Update regularly** - Keep Docker and system packages updated
5. **Monitor logs** - Set up log aggregation (CloudWatch, etc.)
6. **Backup data** - Regular backups of artifacts

## Cost Optimization

- **t3.medium** ($30-40/month) - Development/testing
- **t3.large** ($60-70/month) - Production (recommended)
- **EBS storage** - Use gp3 volumes (cheaper than gp2)
- **Elastic IP** - Free when instance is running
- **Data transfer** - First 100 GB/month free

## Next Steps

1. Set up reverse proxy with SSL (Caddy/Traefik)
2. Configure domain name (Route 53)
3. Set up CloudWatch monitoring
4. Configure automated backups
5. Implement log aggregation
6. Set up CI/CD pipeline (GitHub Actions → EC2)

