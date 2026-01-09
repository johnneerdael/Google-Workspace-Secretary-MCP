# Google Workspace Secretary MCP

[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](https://github.com/johnneerdael/Google-Workspace-Secretary-MCP/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

An AI-native Model Context Protocol (MCP) server that transforms your Gmail and Google Calendar into an intelligent, programmable assistant for Claude and other AI systems.

[📚 **Full Documentation**](https://johnneerdael.github.io/Google-Workspace-Secretary-MCP/) · [🚀 **Quick Start**](#-quick-start) · [🔒 **Security**](#-security-best-practices)

---

## What's New in v2.0.0

**Local-First Architecture** — The server now operates like a proper email client (Thunderbird, Apple Mail) with a local SQLite cache:

- ⚡ **Instant Reads**: Email queries hit local SQLite instead of IMAP — sub-millisecond response times
- 🔄 **Background Sync**: Continuous incremental sync keeps your cache fresh (every 5 minutes)
- 💾 **Persistent Cache**: Survives restarts; only fetches new emails after initial sync
- 📊 **RFC-Compliant**: Proper UIDVALIDITY/UIDNEXT tracking per RFC 3501/4549

See the [Architecture Documentation](https://johnneerdael.github.io/Google-Workspace-Secretary-MCP/architecture.html) for technical details.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **Intelligent Triage** | Auto-detect VIPs, questions, deadlines, and meeting requests |
| **Timezone-Aware Scheduling** | All calendar ops respect your configured timezone and working hours |
| **Document Intelligence** | Extract content from PDF/DOCX attachments directly into AI context |
| **Safe Actions** | "Draft First" philosophy — AI never sends without your approval |
| **Local-First Cache** | SQLite-backed instant reads with background IMAP sync |

---

## 🚀 Quick Start

### 1. Clone and Configure

```bash
git clone https://github.com/johnneerdael/Google-Workspace-Secretary-MCP.git
cd Google-Workspace-Secretary-MCP

# Create your config
cp config.sample.yaml config/config.yaml
```

### 2. Generate a Secure Bearer Token

**We strongly recommend enabling bearer authentication.** Generate a unique token:

```bash
# macOS / Linux
uuidgen

# Windows (PowerShell)
[guid]::NewGuid().ToString()

# Or use OpenSSL for a longer token
openssl rand -hex 32
```

Add to your `config/config.yaml`:

```yaml
bearer_auth:
  enabled: true
  token: "your-generated-uuid-here"
```

### 3. Configure Email Credentials

Edit `config/config.yaml` with your IMAP/SMTP details:

```yaml
email:
  imap_server: imap.gmail.com
  smtp_server: smtp.gmail.com
  username: your-email@gmail.com
  password: your-app-password  # Use Gmail App Password, not your main password
```

> 💡 **Gmail Users**: You need an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

### 4. Start with Docker

```bash
docker-compose up -d
```

The server exposes a **Streamable HTTP** endpoint at: `http://localhost:8000/mcp`

### 5. Connect Your AI Client

Configure your MCP client to connect:

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "secretary": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer your-generated-uuid-here"
      }
    }
  }
}
```

See the [Client Setup Guide](https://johnneerdael.github.io/Google-Workspace-Secretary-MCP/getting-started.html) for VS Code, Cursor, and other clients.

---

## 🔒 Security Best Practices

| Practice | Why |
|----------|-----|
| **Always enable bearer auth** | Prevents unauthorized access to your email |
| **Use a UUID token** | Cryptographically random, not guessable |
| **Never commit config.yaml** | Contains secrets — it's in `.gitignore` |
| **Use Gmail App Passwords** | Don't expose your main Google password |
| **Run behind firewall** | Don't expose port 8000 to public internet |

See the [Security Guide](https://johnneerdael.github.io/Google-Workspace-Secretary-MCP/guide/security.html) for SSL/TLS setup and advanced security.

---

## 🤖 Usage Examples

Once connected, ask your AI assistant:

```
"Give me my daily briefing"
→ Summarizes priority emails, today's calendar, and pending action items

"Triage my inbox - what needs attention?"
→ Identifies VIP messages, questions directed at you, and deadline mentions

"Draft a reply to Sarah's meeting request accepting for Tuesday"
→ Creates a draft (never sends automatically) for your review

"What's on my calendar this week?"
→ Lists events with timezone-aware times

"Find all emails from John about the Q4 report"
→ Searches local cache for instant results
```

---

## 📁 Project Structure

```
Google-Workspace-Secretary-MCP/
├── config/
│   ├── config.yaml          # Your configuration (git-ignored)
│   └── email_cache.db       # SQLite cache (auto-created)
├── workspace_secretary/
│   ├── server.py            # MCP server + background sync
│   ├── tools.py             # All MCP tools
│   ├── cache.py             # SQLite cache layer
│   └── ...
├── docs/                    # VitePress documentation
├── docker-compose.yml
└── config.sample.yaml       # Template config
```

---

## 📚 Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](https://johnneerdael.github.io/Google-Workspace-Secretary-MCP/getting-started.html) | Full installation and client setup |
| [Configuration](https://johnneerdael.github.io/Google-Workspace-Secretary-MCP/guide/configuration.html) | All config.yaml options explained |
| [Docker Guide](https://johnneerdael.github.io/Google-Workspace-Secretary-MCP/guide/docker.html) | Container setup and volume persistence |
| [Architecture](https://johnneerdael.github.io/Google-Workspace-Secretary-MCP/architecture.html) | v2.0 local-first design and SQLite schema |
| [Security](https://johnneerdael.github.io/Google-Workspace-Secretary-MCP/guide/security.html) | Bearer auth, SSL, and best practices |
| [Agent Workflows](https://johnneerdael.github.io/Google-Workspace-Secretary-MCP/guide/agents.html) | HITL rules and safe action patterns |
| [API Reference](https://johnneerdael.github.io/Google-Workspace-Secretary-MCP/api/) | All available tools and resources |

---

## 🛠️ Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run locally (without Docker)
python -m workspace_secretary.server
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

Built with the [Model Context Protocol](https://modelcontextprotocol.io/) · [GitHub](https://github.com/johnneerdael/Google-Workspace-Secretary-MCP)
