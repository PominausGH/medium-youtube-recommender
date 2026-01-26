# Deployment Guide

This guide covers deploying AI Content Curator to a VPS or any Linux server.

## Prerequisites

- Linux server (Ubuntu 20.04+ recommended)
- Docker and Docker Compose installed
- Domain name (optional, for SSL)
- OpenAI API key

## Quick Start (Development)

```bash
# Clone the repository
git clone https://github.com/your-repo/ai-content-curator.git
cd ai-content-curator

# Copy and configure environment
cp .env.example .env
nano .env  # Add your OPENAI_API_KEY

# Start with Docker Compose
docker-compose up -d

# Access at http://localhost:8501
```

## Production Deployment

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for docker group
```

### 2. Deploy Application

```bash
# Clone repository
cd /opt
sudo git clone https://github.com/your-repo/ai-content-curator.git
cd ai-content-curator

# Set permissions
sudo chown -R $USER:$USER .

# Configure environment
cp .env.example .env
nano .env
```

Required environment variables:
```bash
OPENAI_API_KEY=sk-your-key-here
ENVIRONMENT=production
LOG_LEVEL=INFO
```

Optional variables:
```bash
GITHUB_TOKEN=ghp_your-token
SENTRY_DSN=https://key@sentry.io/id
OBSIDIAN_VAULT=/path/to/vault
PROJECTS_PATH=/path/to/projects
```

### 3. Create Required Directories

```bash
mkdir -p data logs backups nginx/ssl nginx/logs
```

### 4. Start Services

```bash
# Production mode with nginx
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f app
```

### 5. Configure SSL (Optional but Recommended)

Using Let's Encrypt with Certbot:

```bash
# Install certbot
sudo apt install certbot

# Get certificate (stop nginx first)
docker-compose -f docker-compose.prod.yml stop nginx
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/

# Update nginx.conf to enable SSL (uncomment SSL lines)
nano nginx/nginx.conf

# Restart nginx
docker-compose -f docker-compose.prod.yml up -d nginx
```

Auto-renewal cron:
```bash
# Add to crontab
0 0 1 * * certbot renew --quiet && docker-compose -f /opt/ai-content-curator/docker-compose.prod.yml restart nginx
```

## Maintenance

### Backups

Automatic backups run daily at 2 AM. Manual backup:

```bash
./scripts/backup.sh /opt/ai-content-curator/backups
```

Restore from backup:
```bash
gunzip -c backups/curator_backup_YYYY-MM-DD_HH-MM-SS.db.gz > data/curator.db
docker-compose -f docker-compose.prod.yml restart app
```

### Updates

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### Monitoring

View application logs:
```bash
docker-compose -f docker-compose.prod.yml logs -f app
```

View nginx access logs:
```bash
tail -f nginx/logs/access.log
```

Check container health:
```bash
docker-compose -f docker-compose.prod.yml ps
curl http://localhost:8501/_stcore/health
```

### Troubleshooting

**Container won't start:**
```bash
docker-compose -f docker-compose.prod.yml logs app
```

**Database locked:**
```bash
docker-compose -f docker-compose.prod.yml restart app
```

**Out of memory:**
```bash
# Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

**Permission errors:**
```bash
sudo chown -R 1000:1000 data logs backups
```

## Security Checklist

- [ ] Change default ports if exposed to internet
- [ ] Configure firewall (ufw)
- [ ] Enable SSL/TLS
- [ ] Set strong passwords
- [ ] Keep system and dependencies updated
- [ ] Configure Sentry for error tracking
- [ ] Set up log rotation
- [ ] Configure backup rotation

## Firewall Configuration

```bash
# Allow SSH, HTTP, HTTPS
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

## Resource Requirements

Minimum:
- 1 CPU core
- 1 GB RAM
- 10 GB storage

Recommended:
- 2 CPU cores
- 2 GB RAM
- 20 GB storage

## Architecture

```
                    ┌─────────────┐
                    │   Internet  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    Nginx    │ :80/:443
                    │  (reverse   │
                    │   proxy)    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Streamlit  │ :8501
                    │    App      │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌────▼────┐ ┌─────▼─────┐
        │  SQLite   │ │ OpenAI  │ │ External  │
        │  Database │ │   API   │ │   APIs    │
        └───────────┘ └─────────┘ └───────────┘
```

## Support

For issues, check:
1. Container logs
2. Application logs in `logs/`
3. GitHub Issues
