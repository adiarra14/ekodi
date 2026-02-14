#!/bin/bash
# ── Ekodi.ai – Nginx + Certbot Setup Script ─────────────────
# Run on: 145.223.79.71 (Ubuntu 24.04, Portainer VPS)
# Prerequisites: Nginx 1.24+, Certbot 2.9+, DNS A record for ekodi.ai → 145.223.79.71
#
# Usage: sudo bash setup-ekodi-nginx.sh

set -e

DOMAIN="ekodi.ai"
WWW_DOMAIN="www.ekodi.ai"
APP_PORT=9001
EMAIL="admin@ekodi.ai"
NGINX_CONF="/etc/nginx/sites-available/${DOMAIN}"
NGINX_LINK="/etc/nginx/sites-enabled/${DOMAIN}"

echo "══════════════════════════════════════════════"
echo "  Ekodi.ai – Nginx + SSL Setup"
echo "══════════════════════════════════════════════"
echo ""
echo "  Domain:  ${DOMAIN} / ${WWW_DOMAIN}"
echo "  Proxy:   localhost:${APP_PORT}"
echo "  Email:   ${EMAIL}"
echo ""

# ── Step 1: Check DNS ────────────────────────────────────────
echo "[1/5] Checking DNS..."
RESOLVED_IP=$(dig +short ${DOMAIN} 2>/dev/null | head -1)
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "unknown")

if [ -z "$RESOLVED_IP" ]; then
    echo "  ⚠ WARNING: ${DOMAIN} does not resolve yet."
    echo "  Make sure your DNS A record points to ${SERVER_IP}"
    echo "  Certbot will FAIL without DNS configured."
    read -p "  Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "  Aborted. Configure DNS first."
        exit 1
    fi
else
    echo "  ${DOMAIN} → ${RESOLVED_IP}"
    if [ "$RESOLVED_IP" != "$SERVER_IP" ]; then
        echo "  ⚠ WARNING: DNS resolves to ${RESOLVED_IP} but server IP is ${SERVER_IP}"
        read -p "  Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then exit 1; fi
    else
        echo "  ✓ DNS matches server IP"
    fi
fi

# ── Step 2: Create Nginx config (HTTP only first) ───────────
echo ""
echo "[2/5] Creating Nginx config..."

cat > ${NGINX_CONF} << 'NGINX_EOF'
# ── ekodi.ai – Nginx reverse proxy ──────────────────────────
# Proxies to Docker container on port 9001

# Redirect www to non-www
server {
    listen 80;
    listen [::]:80;
    server_name www.ekodi.ai;
    return 301 http://ekodi.ai$request_uri;
}

# Main server block
server {
    listen 80;
    listen [::]:80;
    server_name ekodi.ai;

    # Certbot challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Proxy to ekodi app
    location / {
        proxy_pass http://127.0.0.1:9001;
        proxy_http_version 1.1;

        # WebSocket support (for future live features)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Standard proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts (AI responses can be slow)
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
        proxy_connect_timeout 10s;

        # Large file uploads (voice recordings)
        client_max_body_size 25M;
    }
}
NGINX_EOF

echo "  ✓ Config written to ${NGINX_CONF}"

# ── Step 3: Enable site + test config ────────────────────────
echo ""
echo "[3/5] Enabling site..."

# Create symlink if it doesn't exist
if [ ! -L "${NGINX_LINK}" ]; then
    ln -s ${NGINX_CONF} ${NGINX_LINK}
    echo "  ✓ Symlink created"
else
    echo "  ✓ Symlink already exists"
fi

# Test nginx config
nginx -t
echo "  ✓ Nginx config OK"

# Reload nginx
systemctl reload nginx
echo "  ✓ Nginx reloaded"

# ── Step 4: Get SSL certificate ──────────────────────────────
echo ""
echo "[4/5] Obtaining SSL certificate with Certbot..."
echo "  This will modify the Nginx config to add HTTPS."
echo ""

certbot --nginx \
    -d ${DOMAIN} \
    -d ${WWW_DOMAIN} \
    --email ${EMAIL} \
    --agree-tos \
    --no-eff-email \
    --redirect

echo "  ✓ SSL certificate obtained and configured"

# ── Step 5: Verify auto-renewal ──────────────────────────────
echo ""
echo "[5/5] Verifying Certbot auto-renewal..."
certbot renew --dry-run
echo "  ✓ Auto-renewal is working"

# ── Done ─────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo "  ✓ Setup complete!"
echo ""
echo "  https://ekodi.ai  →  localhost:${APP_PORT}"
echo ""
echo "  Next steps:"
echo "  1. Deploy the ekodi stack in Portainer"
echo "     (compose file: ekodi-port.yml)"
echo "  2. Set environment variables in Portainer"
echo "  3. Visit https://ekodi.ai"
echo "══════════════════════════════════════════════"
