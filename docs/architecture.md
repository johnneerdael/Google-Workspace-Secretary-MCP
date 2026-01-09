# Architecture v3.0.0

This document describes the dual-process architecture introduced in v3.0.0.

## Overview

The Google Workspace Secretary MCP uses a **dual-process architecture** that separates concerns:

- **Engine** (`secretary-engine`): Headless sync daemon that owns data
- **MCP** (`secretary-mcp`): AI interface layer that serves tools

```
┌─────────────────────────────────────────────────────────────┐
│  secretary-engine (standalone daemon)                       │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐   │
│  │ IMAP Sync   │  │ Calendar    │  │ Internal API      │   │
│  │ (OAuth2)    │  │ Sync        │  │ (Unix Socket)     │   │
│  └──────┬──────┘  └──────┬──────┘  └─────────┬─────────┘   │
│         │                │                   │              │
│         ▼                ▼                   ▼              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Database (SQLite or PostgreSQL)        │   │
│  │  • email_cache (emails, threads, folders)           │   │
│  │  • calendar_cache (events, calendars)               │   │
│  │  • embeddings (optional, pgvector)                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ Unix Socket (mutations)
                           │ Database (reads)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  secretary-mcp (MCP server)                                 │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐   │
│  │ MCP Tools   │  │ MCP         │  │ Bearer Auth       │   │
│  │ (email,cal) │  │ Resources   │  │ (for clients)     │   │
│  └─────────────┘  └─────────────┘  └───────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Aspect | Engine | MCP |
|--------|--------|-----|
| **Auth** | OAuth2 (Gmail/Calendar APIs) | Bearer token (for AI clients) |
| **Lifecycle** | Always running, independent | Stateless, can restart anytime |
| **Data ownership** | Owns database, syncs continuously | Reads from database |
| **Mutations** | Handles all writes via internal API | Calls Engine API |
| **Entry point** | `python -m workspace_secretary.engine` | `python -m workspace_secretary` |

## Database Backends

### SQLite (Default)

Best for simple deployment and single-user scenarios.

```yaml
database:
  backend: sqlite
  sqlite:
    email_cache_path: config/email_cache.db
    calendar_cache_path: config/calendar_cache.db
```

**Features:**
- WAL mode for concurrent reads
- FTS5 for full-text search
- Zero configuration
- Single-file deployment

### PostgreSQL + pgvector (AI Features)

Required when you want semantic search and AI-powered features.

```yaml
database:
  backend: postgres
  postgres:
    host: localhost
    port: 5432
    database: secretary
    user: secretary
    password: ${POSTGRES_PASSWORD}
  
embeddings:
  enabled: true
  endpoint: https://api.openai.com/v1/embeddings
  model: text-embedding-3-small
  api_key: ${OPENAI_API_KEY}
  dimensions: 1536
```

**Features:**
- pgvector for vector similarity search
- Semantic email search ("find emails about project deadlines")
- Related email detection
- Context retrieval for AI drafting (RAG)
- HNSW indexing for fast similarity queries

## Internal API

The Engine exposes a FastAPI server on Unix socket for mutations:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Health check, sync status |
| `/api/sync/trigger` | POST | Trigger immediate sync |
| `/api/email/move` | POST | Move email to folder |
| `/api/email/mark-read` | POST | Mark email as read |
| `/api/email/mark-unread` | POST | Mark email as unread |
| `/api/email/labels` | POST | Modify Gmail labels |
| `/api/calendar/event` | POST | Create calendar event |
| `/api/calendar/respond` | POST | Accept/decline meeting |

## Database Schema

### Email Cache

```sql
CREATE TABLE emails (
    uid INTEGER,
    folder TEXT,
    message_id TEXT,
    subject TEXT,
    from_addr TEXT,
    to_addr TEXT,
    cc_addr TEXT,
    date TEXT,
    body_text TEXT,
    body_html TEXT,
    flags TEXT,
    is_unread INTEGER,
    is_important INTEGER,
    modseq INTEGER,
    in_reply_to TEXT,
    references_header TEXT,
    thread_root TEXT,
    thread_parent_uid INTEGER,
    thread_depth INTEGER,
    PRIMARY KEY (uid, folder)
);

CREATE TABLE folder_state (
    folder TEXT PRIMARY KEY,
    uidvalidity INTEGER,
    uidnext INTEGER,
    highestmodseq INTEGER,
    last_sync TEXT
);
```

### Calendar Cache

```sql
CREATE TABLE calendars (
    id TEXT PRIMARY KEY,
    summary TEXT,
    description TEXT,
    timezone TEXT,
    access_role TEXT,
    sync_token TEXT,
    last_sync TEXT
);

CREATE TABLE events (
    id TEXT PRIMARY KEY,
    calendar_id TEXT,
    summary TEXT,
    description TEXT,
    location TEXT,
    start_time TEXT,
    end_time TEXT,
    all_day INTEGER,
    status TEXT,
    organizer_email TEXT,
    recurrence TEXT,
    recurring_event_id TEXT,
    html_link TEXT,
    hangout_link TEXT,
    created TEXT,
    updated TEXT,
    etag TEXT,
    raw_json TEXT
);

CREATE TABLE attendees (
    event_id TEXT,
    email TEXT,
    display_name TEXT,
    response_status TEXT,
    is_organizer INTEGER,
    is_self INTEGER,
    PRIMARY KEY (event_id, email)
);
```

### Embeddings (PostgreSQL only)

```sql
CREATE TABLE email_embeddings (
    email_uid INTEGER,
    email_folder TEXT,
    embedding vector(1536),
    model TEXT,
    content_hash TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (email_uid, email_folder)
);

CREATE INDEX idx_email_embeddings_vector 
ON email_embeddings USING hnsw (embedding vector_cosine_ops);
```

## Sync Strategy

### Email Sync
1. **Initial**: Full sync of INBOX (newest first, batch of 50)
2. **Incremental**: UIDNEXT-based delta sync every 5 minutes
3. **Threading**: RFC 5256 THREAD/SORT when available, References-based fallback

### Calendar Sync
1. **Initial**: Full sync (all events, no time limit for historical data)
2. **Incremental**: Sync token-based delta sync
3. **Fallback**: Full resync on 410 (sync token expired)

## Deployment Options

### Single Process (Development)

```bash
# Runs both Engine and MCP in one process (legacy mode)
docker-compose -f docker-compose.single.yaml up
```

### Dual Process (Production)

```bash
# Runs Engine and MCP as separate services
docker-compose up
```

### Docker Compose (Dual Process)

```yaml
services:
  engine:
    build: .
    command: ["uv", "run", "python", "-m", "workspace_secretary.engine"]
    volumes:
      - ./config:/app/config
      - engine-socket:/tmp
    environment:
      - ENGINE_SOCKET=/tmp/secretary-engine.sock

  mcp:
    build: .
    command: ["uv", "run", "python", "-m", "workspace_secretary"]
    volumes:
      - ./config:/app/config:ro
      - engine-socket:/tmp:ro
    ports:
      - "8000:8000"
    depends_on:
      engine:
        condition: service_healthy

volumes:
  engine-socket:
```

## AI Features (pgvector)

When PostgreSQL + embeddings are configured, additional capabilities are unlocked:

### Semantic Search

Find emails by meaning, not just keywords:

```python
# "Find emails about project deadlines" matches:
# - "We need to finish by end of quarter"
# - "Timeline for the deliverable"
# - "When is this due?"
```

### Related Emails

Find contextually similar emails:

```python
# Given an email about "Q4 budget planning"
# Returns related emails about:
# - Previous budget discussions
# - Q3 budget review
# - Financial planning meetings
```

### RAG Context

Automatically retrieve relevant context for drafting replies:

```python
# When drafting a reply, system fetches:
# - Previous emails in thread
# - Semantically related emails
# - Relevant calendar events
```

## Performance Characteristics

| Operation | SQLite | PostgreSQL |
|-----------|--------|------------|
| Email query (cached) | <1ms | <5ms |
| Full-text search | 10-50ms | 5-20ms |
| Semantic search | N/A | 20-100ms |
| Initial sync (1000 emails) | 30-60s | 30-60s |
| Incremental sync | <1s | <1s |

## Migration Path

1. **v2.x → v3.0**: Automatic. Existing SQLite cache is preserved.
2. **SQLite → PostgreSQL**: Export/import tool provided (see `docs/guide/migration.md`)
