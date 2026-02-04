# Remote Access Setup

Guide for accessing Demi from outside your home network.

## Overview

By default, Demi is only accessible on your local network. To use the mobile app while away from home, you need to set up remote access.

## Recommended: Cloudflare Tunnel (Free)

Cloudflare Tunnel provides a secure, free way to expose Demi to the internet without opening ports on your router.

### Step 1: Install cloudflared

```bash
# On your server (where Demi runs)
# Download and install cloudflared
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Or use Docker
docker pull cloudflare/cloudflared:latest
```

### Step 2: Authenticate

```bash
cloudflared tunnel login
```

This will open a browser to authenticate with Cloudflare.

### Step 3: Create a Tunnel

```bash
# Create a tunnel
cloudflared tunnel create demi-server

# The output will show your tunnel ID, save it
# Example: 7f3e...8a2b
```

### Step 4: Configure the Tunnel

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: /home/YOUR_USERNAME/.cloudflared/YOUR_TUNNEL_ID.json

ingress:
  # Mobile API
  - hostname: demi-api.yourdomain.com
    service: http://localhost:8081
  
  # Dashboard
  - hostname: demi.yourdomain.com
    service: http://localhost:8080
  
  # Default - reject other requests
  - service: http_status:404
```

### Step 5: Add DNS Records

```bash
# Add DNS records pointing to your tunnel
cloudflared tunnel route dns demi-server demi.yourdomain.com
cloudflared tunnel route dns demi-server demi-api.yourdomain.com
```

### Step 6: Run the Tunnel

```bash
# Run manually
cloudflared tunnel run demi-server

# Or as a service
sudo cloudflared service install
sudo systemctl start cloudflared
```

### Step 7: Update Flutter App

In `flutter_app/lib/providers/chat_provider.dart`:

```dart
// Change to your Cloudflare domain
static const String serverUrl = 'https://demi-api.yourdomain.com';
```

Rebuild and install the app.

## Alternative: ngrok (Quick Testing)

For quick testing without domain setup:

```bash
# Install ngrok
# From: https://ngrok.com/download

# Expose the mobile API
ngrok http 8081

# The output shows a public URL like:
# https://abc123.ngrok.io

# Update Flutter app to use this URL
```

**Note:** ngrok URLs change every restart (unless you pay). Use Cloudflare Tunnel for permanent access.

## Alternative: Reverse Proxy (Advanced)

If you have your own domain and want full control:

### Using Nginx

```nginx
# /etc/nginx/sites-available/demi
server {
    listen 443 ssl http2;
    server_name demi.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

server {
    listen 443 ssl http2;
    server_name demi-api.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Port Forwarding (Not Recommended)

If you want to expose directly (security risk):

1. Set static IP on your server
2. Forward ports 8080-8081 on your router
3. Use a dynamic DNS service (No-IP, DuckDNS)
4. Set up SSL with Let's Encrypt

**Warning:** Opening ports exposes you to security risks. Use tunnels instead.

## Security Considerations

1. **Always use HTTPS** - Never expose HTTP to the internet
2. **Authentication** - Demi has no built-in auth on the mobile API
3. **IP Restrictions** - Cloudflare can restrict by IP/country
4. **Rate Limiting** - Consider adding rate limits at the proxy level

## Testing Remote Access

Once set up:

```bash
# Test API endpoint
curl https://demi-api.yourdomain.com/api/health

# Test WebSocket
wss://demi-api.yourdomain.com/ws/chat/test
```

## Troubleshooting

### Connection refused
- Check Docker container is running
- Verify port mapping in docker-compose.yml
- Check firewall rules

### SSL errors
- Ensure certificates are valid
- Check domain DNS is pointing correctly
- Verify system time is correct

### WebSocket fails
- Ensure proxy passes Upgrade headers
- Check WebSocket URL uses wss:// not ws://
- Verify no firewall blocking WebSocket

## Mobile App Configuration

Update the Flutter app for remote access:

```dart
// In lib/providers/chat_provider.dart

// For local testing:
// static const String serverUrl = 'http://192.168.1.245:8081';

// For remote access:
static const String serverUrl = 'https://demi-api.yourdomain.com';
```

Rebuild the app and install on your phone.

## Docker Compose Integration

Add Cloudflare Tunnel to docker-compose.yml:

```yaml
services:
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: demi-tunnel
    command: tunnel --no-autoupdate run --token YOUR_TUNNEL_TOKEN
    restart: unless-stopped
    depends_on:
      - backend
```

Get your token from the Cloudflare dashboard (Zero Trust > Access > Tunnels).
