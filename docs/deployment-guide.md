# War of Names — OVH VPS Deployment Guide

> Single-server, Docker-based deployment on Debian Linux.
> Target: production-style HTTP/HTTPS stack with Caddy + nginx + FastAPI + PostgreSQL.

---

## Architecture Overview

```
Internet
    │
    ▼ (port 443 → HTTPS, port 80 → redirect)
┌─────────────────────────────────────────────────┐
│  OVH Debian VPS                                 │
│                                                 │
│  Caddy (host-level reverse proxy)               │
│    ├── yourdomain.com → localhost:8080           │
│    └── auto HTTPS via Let's Encrypt             │
│                                                 │
│  ┌─── Docker Compose Network ────────────────┐  │
│  │                                           │  │
│  │  frontend (nginx)  ←─── :8080 mapped      │  │
│  │    ├── serves built SPA                   │  │
│  │    ├── proxies /api/ → api:8000           │  │
│  │    ├── proxies /l/   → api:8000           │  │
│  │    └── serves /landing                    │  │
│  │                                           │  │
│  │  api (uvicorn)     ←─── internal only     │  │
│  │    └── connects to db:5432                │  │
│  │                                           │  │
│  │  db (postgres)     ←─── internal only     │  │
│  │    └── pgdata volume                      │  │
│  │                                           │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  /opt/war-of-names/                             │
│    ├── .env (secrets, NOT in git)               │
│    ├── backups/ (pg_dump daily)                  │
│    └── (git clone of repo)                      │
│                                                 │
│  cron: daily pg_dump → /opt/war-of-names/backups│
└─────────────────────────────────────────────────┘
```

**What is public:** Only Caddy on ports 80/443.
**What is internal:** nginx container on 127.0.0.1:8080, API on Docker network only, PostgreSQL on Docker network only.
**How frontend talks to backend:** nginx proxies `/api/` and `/l/` to `api:8000` over the Docker network.
**How backend talks to DB:** SQLAlchemy connects to `db:5432` over the Docker network.

---

## Why Caddy?

- Automatic HTTPS via Let's Encrypt — zero cert management
- Automatic HTTP → HTTPS redirect
- Automatic certificate renewal
- Single binary, Debian package available
- The Docker-internal nginx handles SPA routing and API proxy (already built) — Caddy just adds TLS termination in front

---

## Pre-Deployment Checklist

Before starting the server setup, ensure:

- [ ] You have an OVH VPS with Debian 11+ or 12
- [ ] You have root SSH access to the VPS
- [ ] You have a domain name ready to point to the VPS
- [ ] The project repository is on GitHub (public or you have deploy access)
- [ ] The `docker-compose.yml` binds frontend to `127.0.0.1:8080:80` (not `80:80`)
- [ ] The `.env.example` file has the production template with `JWT_SECRET` field

---

## Phase 1 — Initial Server Hardening

SSH into the VPS as root:

```bash
ssh root@YOUR_VPS_IP
```

### 1.1 Update the system

```bash
apt update && apt upgrade -y
```

### 1.2 Create a deploy user

```bash
adduser deploy
usermod -aG sudo deploy
```

### 1.3 Set up SSH key auth for the deploy user

```bash
mkdir -p /home/deploy/.ssh
cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
```

### 1.4 Disable root password login

```bash
sed -i 's/^PermitRootLogin yes/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sed -i 's/^#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd
```

> **Test before logging out:** Open a new terminal and verify `ssh deploy@YOUR_VPS_IP` works.

---

## Phase 2 — Firewall

```bash
apt install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
ufw status
```

**Result:** Only ports 22, 80, 443 are open. Docker containers, DB, API — all unreachable from outside.

---

## Phase 3 — Install Docker

```bash
# Install prerequisites
apt install -y ca-certificates curl gnupg

# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/debian \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list

# Install Docker Engine + Compose plugin
apt update
apt install -y docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin

# Add deploy user to docker group
usermod -aG docker deploy

# Verify
docker --version
docker compose version
```

---

## Phase 4 — Clone Project and Configure

```bash
# Switch to deploy user
su - deploy

# Clone the repo
git clone https://github.com/YOUR_USERNAME/War-of-Names.git /opt/war-of-names
cd /opt/war-of-names

# Create production .env from template
cp .env.example .env
```

### 4.1 Generate secrets

```bash
echo "DB_PASSWORD=$(openssl rand -base64 24)"
echo "JWT_SECRET=$(openssl rand -hex 32)"
```

### 4.2 Edit .env with real values

```bash
nano .env
```

Fill in:

```env
APP_ENV=production
DEBUG=false
APP_HOST=0.0.0.0
APP_PORT=8000

DB_HOST=db
DB_PORT=5432
DB_NAME=war_of_names
DB_USER=warofnames
DB_PASSWORD=<paste generated password>

CORS_ORIGIN=https://yourdomain.com

JWT_SECRET=<paste generated secret>
```

---

## Phase 5 — First Deploy (HTTP Validation)

```bash
cd /opt/war-of-names

# Build and start all containers
docker compose up -d --build

# Watch logs until you see "Application startup complete"
docker compose logs -f
# (Ctrl+C when ready)

# Verify containers are healthy
docker compose ps
```

### 5.1 Verify from the server

```bash
# SPA loads
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8080

# API works through nginx
curl -s http://127.0.0.1:8080/health

# Game info endpoint
curl -s http://127.0.0.1:8080/api/game-info | head -c 120

# Landing page
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8080/landing

# Tracked links proxy
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8080/l/test
```

---

## Phase 6 — DNS Setup

Before installing Caddy, point your domain to the VPS.

### 6.1 Set DNS A Record

In your domain registrar or DNS provider:

```
Type: A
Name: @ (or yourdomain.com)
Value: YOUR_VPS_IP
TTL: 300
```

Optional — if you want `www` too:

```
Type: CNAME
Name: www
Value: yourdomain.com
TTL: 300
```

### 6.2 Verify DNS propagation

```bash
# From the server or any machine
dig +short yourdomain.com
# Should return YOUR_VPS_IP

# Or use an online tool: https://dnschecker.org
```

Wait for propagation (usually 5–30 minutes) before proceeding.

---

## Phase 7 — Install Caddy (HTTPS Reverse Proxy)

```bash
# Switch back to root for package installation
sudo su -

# Install Caddy
apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | tee /etc/apt/sources.list.d/caddy-stable.list
apt update
apt install -y caddy
```

### 7.1 Configure Caddy

```bash
nano /etc/caddy/Caddyfile
```

Write this (replace `yourdomain.com` with your actual domain):

```
yourdomain.com {
    reverse_proxy 127.0.0.1:8080
}
```

That's the entire config. Caddy handles:
- Automatic HTTPS via Let's Encrypt
- Automatic HTTP → HTTPS redirect
- Automatic certificate renewal
- Reverse proxy to Docker frontend

### 7.2 Start Caddy

```bash
systemctl reload caddy
systemctl enable caddy
systemctl status caddy
```

### 7.3 Verify HTTPS

```bash
curl -I https://yourdomain.com
curl -s https://yourdomain.com/health
curl -s https://yourdomain.com/api/game-info | head -c 120
curl -s -o /dev/null -w "HTTP %{http_code}\n" https://yourdomain.com/landing
```

---

## Phase 8 — Backups

### 8.1 Make scripts executable

```bash
chmod +x /opt/war-of-names/scripts/backup.sh
chmod +x /opt/war-of-names/scripts/restore.sh
chmod +x /opt/war-of-names/scripts/deploy.sh
```

### 8.2 Create backup directory

```bash
mkdir -p /opt/war-of-names/backups
```

### 8.3 Test backup manually

```bash
/opt/war-of-names/scripts/backup.sh
```

### 8.4 Schedule daily backups via cron

```bash
crontab -e
```

Add this line (daily at 3 AM):

```
0 3 * * * /opt/war-of-names/scripts/backup.sh >> /opt/war-of-names/backups/cron.log 2>&1
```

### 8.5 Backup details

| Item              | Value                                    |
|-------------------|------------------------------------------|
| Method            | `pg_dump` via Docker, gzipped            |
| Schedule          | Daily at 3 AM via cron                   |
| Retention         | 14 days (auto-deleted)                   |
| Location          | `/opt/war-of-names/backups/`             |
| Restore command   | `./scripts/restore.sh <backup_file>`     |

### 8.6 Restoring from backup

```bash
cd /opt/war-of-names

# List available backups
ls -lh backups/*.sql.gz

# Restore (interactive — asks for confirmation)
./scripts/restore.sh backups/war_of_names_20260321_030000.sql.gz
```

> **Warning:** Restore drops and recreates the database. Make sure you have the right backup file.

---

## Phase 9 — Final Verification

Run all of these after setup is complete:

```bash
echo "=== Containers ==="
docker compose -f /opt/war-of-names/docker-compose.yml ps

echo "=== HTTPS ==="
curl -sI https://yourdomain.com | head -3

echo "=== Health ==="
curl -s https://yourdomain.com/health

echo "=== API ==="
curl -s https://yourdomain.com/api/game-info | head -c 120

echo "=== Landing ==="
curl -s -o /dev/null -w "HTTP %{http_code}\n" https://yourdomain.com/landing

echo "=== Firewall ==="
ufw status

echo "=== Backups ==="
ls -la /opt/war-of-names/backups/

echo "=== Caddy ==="
systemctl status caddy --no-pager
```

---

## Deployment Workflow (After First Deploy)

When you push code changes to GitHub:

```bash
ssh deploy@YOUR_VPS_IP
cd /opt/war-of-names
./scripts/deploy.sh
```

The script does: `git pull` → `docker compose up -d --build` → health check → verify.

### Manual alternative

```bash
cd /opt/war-of-names
git pull origin main
docker compose up -d --build
docker compose ps
curl -s http://127.0.0.1:8080/health
```

### Rollback

```bash
# Check what went wrong
docker compose logs api --tail 50

# Roll back to previous commit
git log --oneline -5
git checkout <good_commit_hash>
docker compose up -d --build

# If DB is corrupted, restore from backup
./scripts/restore.sh backups/war_of_names_YYYYMMDD_030000.sql.gz
```

---

## Worker / Scheduler Decision

### Current state

There is **no scheduler/worker code** in the project. All game operations (cycle start/end, quiz open/close, item grants, point distributions) are manually triggered by the admin via HTTP endpoints.

### For launch

Deploy as-is. The admin operates the game manually. This is viable for a platform with one active competition where the admin is engaged.

### Post-launch (when needed)

When you want automated operations (auto-start cycles, execute scheduled distributions, expire items), add an APScheduler-based worker:

```yaml
# Add to docker-compose.yml
  worker:
    build: ./backend
    command: python -m app.worker
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
```

This is future work, not a deploy blocker.

---

## Useful Commands Reference

### Container management

```bash
cd /opt/war-of-names

# View running containers
docker compose ps

# View logs (all services)
docker compose logs -f

# View logs (single service)
docker compose logs api --tail 100

# Restart a single service
docker compose restart api

# Full rebuild
docker compose up -d --build

# Stop everything
docker compose down

# Stop everything AND delete data (destructive)
docker compose down -v
```

### Database access

```bash
# Open psql shell inside the db container
docker compose exec db psql -U warofnames -d war_of_names

# Run a query directly
docker compose exec db psql -U warofnames -d war_of_names -c "SELECT count(*) FROM account;"
```

### Caddy management

```bash
systemctl status caddy
systemctl reload caddy
systemctl restart caddy
journalctl -u caddy --no-pager --since "1 hour ago"
```

### Firewall

```bash
ufw status
ufw status verbose
```

---

## Docker Log Rotation (Recommended)

Prevent Docker logs from filling the disk:

```bash
sudo nano /etc/docker/daemon.json
```

```json
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    }
}
```

```bash
sudo systemctl restart docker
```

---

## Honest Status Classification

### ✅ Ready Now
- Docker Compose production stack (frontend + API + DB)
- nginx serves built SPA with API proxy
- API and DB internal-only (not reachable from internet)
- Health checks and restart policies
- Caddy for automatic HTTPS
- Firewall (ufw) — only 22/80/443
- Daily PostgreSQL backups with 14-day retention
- Deploy script for git pull → rebuild → verify
- `.env` separation (secrets not in git)

### ⚠️ Required Before Launch
- Set real `JWT_SECRET` in `.env` on server
- Set real `DB_PASSWORD` in `.env` on server
- Set real `CORS_ORIGIN` to your domain
- Point DNS A record to VPS IP
- Run first deploy and verify HTTPS works

### 🔶 Recommended Next
- Off-server backup copy (rsync/scp to another machine)
- Docker log rotation (see section above)
- Uptime monitoring (UptimeRobot free tier or similar)
- Rate limiting in nginx (`limit_req_zone`)

### 🔷 Optional Later
- Scheduler/worker service for automated game operations
- CI/CD via GitHub Actions (currently manual deploy is fine)
- Database migrations tool (currently `create_all` + schema patches)
- Fail2ban for SSH brute-force protection
- Multi-server setup (only if you outgrow the VPS)
