# Docker Deployment

This guide covers deploying Google Workspace Secretary MCP using Docker, including the v2.0 local-first architecture with SQLite caching.

## Prerequisites

- Docker and Docker Compose installed
- A `config.yaml` file prepared (see [Configuration](configuration.md))

## Quick Start

**1. Clone and configure:**

```bash
git clone https://github.com/johnneerdael/Google-Workspace-Secretary-MCP.git
cd Google-Workspace-Secretary-MCP

# Create config directory and copy sample
mkdir -p config
cp config.sample.yaml config/config.yaml
```

**2. Generate a secure bearer token:**

```bash
# macOS / Linux
uuidgen

# Windows PowerShell
[guid]::NewGuid().ToString()
```

Add to `config/config.yaml`:

```yaml
bearer_auth:
  enabled: true
  token: "your-generated-uuid-here"
```

**3. Start the service:**

```bash
docker-compose up -d
```

**4. Monitor initial sync:**

```bash
docker-compose logs -f
```

On first start, you'll see the background sync progress as emails are downloaded to the SQLite cache.

## Volume Mounts

The Docker container uses volumes to persist critical data:

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `./config/` | `/app/config/` | Configuration AND SQLite cache |
| `./credentials.json` | `/app/credentials.json` | OAuth2 client credentials |
| `./token.json` | `/app/token.json` | OAuth2 access tokens |

::: warning Critical: Mount the Entire Config Directory
In v2.0+, the `config/` directory contains both `config.yaml` AND `email_cache.db`. Mount the directory, not individual files:

```yaml
# ✅ Correct - mounts entire directory
volumes:
  - ./config:/app/config

# ❌ Wrong - cache won't persist
volumes:
  - ./config.yaml:/app/config/config.yaml
```
:::

## SQLite Cache Behavior

### Initial Sync

On first startup (or after deleting `email_cache.db`), the server performs a full sync:

1. Connects to IMAP and lists configured folders
2. Downloads email metadata and bodies in batches of 50
3. Stores everything in `config/email_cache.db`
4. Progress is logged: `Syncing INBOX: 500/2500 emails...`

Initial sync time depends on mailbox size:
- ~1,000 emails: 1-2 minutes
- ~10,000 emails: 5-10 minutes
- ~25,000 emails: 15-30 minutes

### Incremental Sync

After initial sync, background sync runs every 5 minutes:

1. Checks UIDNEXT for new emails (RFC 3501)
2. Downloads only new messages
3. Detects and removes deleted emails
4. Typical incremental sync: < 1 second

### Thread Header Backfill (v2.2.0+)

If you're upgrading from v2.1.x or earlier, the first sync after upgrade will backfill thread headers (`In-Reply-To`, `References`) for existing emails:

```
[BACKFILL] Found 26000 emails missing thread headers
[BACKFILL] Progress: 1000/26000 headers fetched
[BACKFILL] Progress: 5000/26000 headers fetched
...
[BACKFILL] Complete: 26000 headers updated
```

**What's happening?**
- The server fetches ONLY headers (not full bodies) from IMAP
- This is fast: ~1000 headers/second on a good connection
- After backfill, thread queries become instant via SQLite

**Backfill is automatic and one-time.** Future syncs download thread headers with every new email.

See [Threading Guide](/guide/threading) for technical details on RFC 5256 support.

### Cache Management

**Reset the cache** (re-download all emails):
```bash
docker-compose stop
rm config/email_cache.db
docker-compose start
```

**View cache stats**:
```bash
docker exec workspace-secretary sqlite3 /app/config/email_cache.db \
  "SELECT folder, COUNT(*) as emails FROM emails GROUP BY folder;"
```

**Check sync state**:
```bash
docker exec workspace-secretary sqlite3 /app/config/email_cache.db \
  "SELECT * FROM folder_state;"
```

## Authentication in Docker

### OAuth2 Setup

When running in Docker, the OAuth redirect needs special handling:

**1. Start container:**
```bash
docker-compose up -d
```

**2. Run auth setup inside container:**
```bash
docker exec -it workspace-secretary \
  uv run python -m workspace_secretary.auth_setup --config /app/config/config.yaml
```

**3. Follow the OAuth flow:**
- Copy the URL printed to your browser
- Login and approve access
- The browser redirects to `localhost:8080`
- Port 8080 is mapped to the container, which captures the token

**4. Restart if needed:**
```bash
docker-compose restart
```

## Environment Variables

Override settings via environment variables in `docker-compose.yml`:

| Variable | Purpose | Default |
|----------|---------|---------|
| `WORKSPACE_TIMEZONE` | IANA timezone for calendar ops | From config.yaml |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `OAUTH_MODE` | `api` or `imap` | From config.yaml |

Example:
```yaml
environment:
  - WORKSPACE_TIMEZONE=Europe/London
  - LOG_LEVEL=DEBUG
```

## Health Checks

The container includes a health check that verifies:
- HTTP server is responding on port 8000
- IMAP connection is active (if configured)

Check health status:
```bash
docker inspect workspace-secretary --format='{{.State.Health.Status}}'
```

## Production Recommendations

### Resource Limits

For large mailboxes (10k+ emails), consider setting memory limits:

```yaml
services:
  workspace-secretary:
    # ... other config ...
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

### Restart Policy

The default `restart: always` ensures the service recovers from crashes:

```yaml
services:
  workspace-secretary:
    restart: always
```

### Logging

Configure log rotation to prevent disk fill:

```yaml
services:
  workspace-secretary:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Connecting Clients

Once running, the server exposes a **Streamable HTTP** endpoint at:

```
http://localhost:8000/mcp
```

With bearer auth enabled, clients must include the header:
```
Authorization: Bearer your-generated-uuid-here
```

See the [Client Setup Guide](clients.md) for Claude Desktop, VS Code, Cursor, and other MCP clients.

## Troubleshooting

### Sync appears stuck

Check logs for IMAP errors:
```bash
docker-compose logs --tail=100 | grep -i error
```

Common causes:
- Invalid IMAP credentials
- Gmail App Password not configured
- Network connectivity issues

### Cache corruption

If you see SQLite errors, reset the cache:
```bash
docker-compose stop
rm config/email_cache.db
docker-compose start
```

### High memory usage during initial sync

Large mailboxes may use significant memory during initial sync. This is temporary and normalizes after sync completes. If needed, increase container memory limits.

### Bearer auth not working

Verify your config has the correct format:
```yaml
bearer_auth:
  enabled: true
  token: "exact-token-from-client-config"
```

The token must match exactly (case-sensitive) between `config.yaml` and your MCP client configuration.
