# Getting Started

Get up and running with Google Workspace Secretary MCP in minutes.

::: tip What's New in v3.0.0
- **PostgreSQL + pgvector** support for semantic search (optional)
- **Simplified authentication** with manual OAuth flow as default
- **IMAP-only architecture** for maximum compatibility
:::

## Prerequisites

Before you begin, ensure you have:

- **Docker and Docker Compose** installed (recommended)
  - [Install Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Google Cloud Project** with:
  - Gmail API and Google Calendar API enabled
  - OAuth2 credentials (`credentials.json`)
- **Claude Desktop** or another MCP-compatible AI client

## Quick Start

### Step 1: Create Configuration

Create a `config.yaml` file with **all available settings**:

```yaml
# =============================================================================
# Google Workspace Secretary MCP - Complete Configuration
# =============================================================================

# User Identity (REQUIRED)
identity:
  email: your-email@gmail.com
  full_name: "Your Full Name"
  aliases:                          # Optional: other email addresses you use
    - your.alias@gmail.com
    - work@company.com

# IMAP Configuration (REQUIRED)
imap:
  host: imap.gmail.com
  port: 993
  username: your-email@gmail.com
  use_ssl: true
  oauth2:
    client_id: YOUR_CLIENT_ID.apps.googleusercontent.com
    client_secret: YOUR_CLIENT_SECRET
    # refresh_token is populated by auth_setup
    # Or set via environment: GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN

# Timezone (REQUIRED) - Must be valid IANA timezone
timezone: Europe/Amsterdam

# Working Hours (REQUIRED)
working_hours:
  start: "09:00"
  end: "17:00"
  workdays: [1, 2, 3, 4, 5]         # 1=Monday, 7=Sunday

# Calendar Integration (Optional)
calendar:
  enabled: true

# VIP Senders (Optional) - Emails from these addresses get priority
vip_senders:
  - boss@company.com
  - ceo@company.com
  - important-client@example.com

# Folder Restrictions (Optional) - Limit which folders are accessible
allowed_folders:
  - INBOX
  - "[Gmail]/Sent Mail"
  - "[Gmail]/Drafts"

# Bearer Authentication (RECOMMENDED for production)
bearer_auth:
  enabled: true
  token: "your-secure-token-here"   # Generate with: openssl rand -hex 32

# Database Configuration (Optional - defaults to SQLite)
database:
  backend: sqlite                   # "sqlite" (default) or "postgres"
  
  # SQLite settings (used when backend: sqlite)
  sqlite:
    email_cache_path: config/email_cache.db
    calendar_cache_path: config/calendar_cache.db
  
  # PostgreSQL settings (used when backend: postgres)
  # postgres:
  #   host: localhost
  #   port: 5432
  #   database: secretary
  #   user: secretary
  #   password: ${POSTGRES_PASSWORD}
  #   ssl_mode: prefer
  
  # Embeddings for semantic search (requires postgres backend)
  # embeddings:
  #   enabled: true
  #   endpoint: https://api.openai.com/v1/embeddings
  #   model: text-embedding-3-small
  #   api_key: ${OPENAI_API_KEY}
  #   dimensions: 1536
  #   batch_size: 100
```

### Step 2: Create Docker Compose

Create a `docker-compose.yml`:

```yaml
services:
  workspace-secretary:
    image: ghcr.io/johnneerdael/google-workspace-secretary-mcp:latest
    container_name: workspace-secretary
    restart: always
    ports:
      - "8080:8080"
      - "8000:8000"
    volumes:
      - ./config.yaml:/app/config.yaml:ro    # Configuration (read-only)
      - ./token.json:/app/token.json         # OAuth tokens (read-write)
      - ./config:/app/config                 # Cache databases
    environment:
      - LOG_LEVEL=INFO
    command: ["--config", "/app/config.yaml", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
```

::: warning Volume Mounts Explained
- `config.yaml` - Your configuration file (read-only is fine)
- `token.json` - OAuth tokens, must be writable for token refresh
- `config/` - Contains SQLite cache databases, must be writable
:::

### Step 3: Run Authentication

The authentication flow uses **manual mode by default**, which works with any OAuth redirect URI:

```bash
# Start container first
docker compose up -d

# Run authentication setup
docker exec -it workspace-secretary uv run python -m workspace_secretary.auth_setup \
  --credentials-file /app/credentials.json \
  --config /app/config.yaml \
  --output /app/config.yaml \
  --token-output /app/token.json
```

This will:
1. Display an authorization URL
2. Ask you to visit the URL and authorize
3. Ask you to paste the redirect URL (containing the auth code)
4. Save tokens to `token.json` and update `config.yaml`

**Auth Setup Options:**

| Flag | Description |
|------|-------------|
| `--credentials-file` | Path to Google OAuth credentials JSON |
| `--client-id` | Client ID (alternative to credentials file) |
| `--client-secret` | Client secret (alternative to credentials file) |
| `--config` | Existing config.yaml to update |
| `--output` | Where to save updated config (default: config.yaml) |
| `--token-output` | Where to save token.json separately |
| `--manual` | Use manual OAuth flow (default) |
| `--browser` | Use automatic browser-based OAuth flow |

### Step 4: Restart and Verify

```bash
# Restart to pick up new tokens
docker compose restart

# Check logs
docker compose logs -f

# Test connection
curl http://localhost:8000/health
```

## Google Cloud Setup

### Create OAuth2 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **Gmail API** and **Google Calendar API**:
   - Navigate to **APIs & Services** → **Library**
   - Search and enable both APIs

4. Configure OAuth Consent Screen:
   - Go to **APIs & Services** → **OAuth consent screen**
   - User type: **External** (or Internal for Workspace)
   - Add your email as test user
   - Add scopes:
     - `https://mail.google.com/`
     - `https://www.googleapis.com/auth/calendar`

5. Create Credentials:
   - Go to **APIs & Services** → **Credentials**
   - Click **Create Credentials** → **OAuth client ID**
   - Application type: **Desktop app** (recommended for manual flow)
   - Download JSON and save as `credentials.json`

::: tip Redirect URI for Manual Flow
The manual OAuth flow works with any redirect URI, including `http://localhost`. This makes it compatible with headless servers and containers.
:::

## Production Deployment

### With Traefik (Automatic HTTPS)

```yaml
# docker-compose.traefik.yml
services:
  traefik:
    image: traefik:v3.2
    command:
      - "--providers.docker=true"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.letsencrypt.acme.email=${ACME_EMAIL}"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - letsencrypt:/letsencrypt

  workspace-secretary:
    image: ghcr.io/johnneerdael/google-workspace-secretary-mcp:latest
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ./token.json:/app/token.json
      - ./config:/app/config
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mcp.rule=Host(`mcp.yourdomain.com`)"
      - "traefik.http.routers.mcp.tls.certresolver=letsencrypt"
    command: ["--config", "/app/config.yaml", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
```

### With Caddy (Automatic HTTPS)

```yaml
# docker-compose.caddy.yml
services:
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data

  workspace-secretary:
    image: ghcr.io/johnneerdael/google-workspace-secretary-mcp:latest
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ./token.json:/app/token.json
      - ./config:/app/config
    command: ["--config", "/app/config.yaml", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
```

**Caddyfile:**
```
mcp.yourdomain.com {
    reverse_proxy workspace-secretary:8000
}
```

### With PostgreSQL + Semantic Search

For AI-powered semantic search capabilities:

```yaml
# docker-compose.postgres.yml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: secretary
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: secretary
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U secretary"]
      interval: 10s
      timeout: 5s
      retries: 5

  workspace-secretary:
    image: ghcr.io/johnneerdael/google-workspace-secretary-mcp:latest
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ./token.json:/app/token.json
      - ./config:/app/config
    command: ["--config", "/app/config.yaml", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]

volumes:
  postgres_data:
```

Update `config.yaml` for PostgreSQL:

```yaml
database:
  backend: postgres
  postgres:
    host: postgres
    port: 5432
    database: secretary
    user: secretary
    password: ${POSTGRES_PASSWORD}
  embeddings:
    enabled: true
    endpoint: https://api.openai.com/v1/embeddings
    model: text-embedding-3-small
    api_key: ${OPENAI_API_KEY}
```

See [Semantic Search Guide](/guide/semantic-search) for details on using vector search.

## Connecting AI Clients

The server uses **Streamable HTTP** transport at: `http://localhost:8000/mcp`

### Claude Desktop

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "workspace-secretary": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

### Claude Code (CLI)

```bash
claude mcp add --transport http workspace-secretary http://localhost:8000/mcp \
  --header "Authorization: Bearer YOUR_TOKEN"
```

### Cursor / VS Code / Other Clients

See [AI Client Configuration](/guide/clients) for complete setup instructions for all supported clients.

## Environment Variables

All configuration can also be set via environment variables:

| Variable | Description |
|----------|-------------|
| `GMAIL_CLIENT_ID` | OAuth2 client ID |
| `GMAIL_CLIENT_SECRET` | OAuth2 client secret |
| `GMAIL_REFRESH_TOKEN` | OAuth2 refresh token |
| `POSTGRES_HOST` | PostgreSQL host |
| `POSTGRES_PORT` | PostgreSQL port |
| `POSTGRES_DATABASE` | PostgreSQL database name |
| `POSTGRES_USER` | PostgreSQL username |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `OPENAI_API_KEY` | OpenAI API key for embeddings |
| `EMBEDDINGS_API_KEY` | Alternative embeddings API key |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Troubleshooting

### OAuth2 "App Not Verified"

Click **Advanced** → **Go to [App Name] (unsafe)**. This is normal for development apps.

### Token Refresh Fails

Re-run auth setup:
```bash
docker exec -it workspace-secretary uv run python -m workspace_secretary.auth_setup \
  --credentials-file /app/credentials.json \
  --output /app/config.yaml \
  --token-output /app/token.json
```

### Permission Denied Errors

1. Ensure `token.json` exists and is writable
2. Verify APIs are enabled in Google Cloud Console
3. Check that OAuth scopes include Gmail and Calendar

### Container Won't Start

```bash
# Check logs
docker compose logs workspace-secretary

# Common issues:
# - config.yaml not found: check volume mount paths
# - Invalid timezone: use IANA format (Europe/Amsterdam, not CET)
# - Missing required fields: check identity.email, working_hours, timezone
```

## Next Steps

- [Configuration Guide](/guide/configuration) - All configuration options
- [Tools Reference](/api/) - Available MCP tools
- [Semantic Search](/guide/semantic-search) - AI-powered email search
- [Agent Patterns](/guide/agents) - Building intelligent workflows

---

**Need help?** [Open an issue on GitHub](https://github.com/johnneerdael/Google-Workspace-Secretary-MCP/issues)
