# Architecture v4.2.2

This document describes the **read/write split architecture** introduced in v4.0.0, with calendar API passthrough added in v4.2.0.

## Overview

The Gmail Secretary MCP uses a **dual-process architecture** with strict separation of concerns:

- **Engine** (`secretary-engine`): Owns all data mutations and external API connections
- **MCP** (`secretary-mcp`): Read-only database access, delegates mutations to Engine

```
┌─────────────────────────────────────────────────────────────────────┐
│  secretary-engine (daemon)                                          │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ IMAP Client │  │ Calendar    │  │ SMTP Client │  │ Embeddings│  │
│  │ (OAuth2)    │  │ API         │  │ (send/draft)│  │ Generator │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬─────┘  │
│         │                │                │               │         │
│         ▼                │                ▼               ▼         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              DatabaseInterface (WRITE)                      │   │
│  │  • upsert_email(), save_folder_state()                      │   │
│  │  • upsert_embedding() (PostgreSQL only)                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              FastAPI Internal API (Unix Socket)             │   │
│  │  /api/email/move, /api/email/send, /api/calendar/events     │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                               │
          ┌────────────────────┴────────────────────┐
          │ Unix Socket (mutations)                 │
          │ Database file/connection (reads)        │
          ▼                                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  secretary-mcp (MCP server)                                         │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              DatabaseInterface (READ-ONLY)                  │   │
│  │  • get_email_by_uid(), search_emails()                      │   │
│  │  • semantic_search() (PostgreSQL only)                      │   │
│  │  • get_thread_emails(), get_synced_folders()                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────────────┐   │
│  │ MCP Tools   │  │ MCP         │  │ EngineClient              │   │
│  │ (40+ tools) │  │ Resources   │  │ (mutation proxy)          │   │
│  └─────────────┘  └─────────────┘  └───────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## The Read/Write Split

### Why This Architecture?

| Problem (v3.x) | Solution (v4.0+) |
|----------------|------------------|
| Engine used `EmailCache` (SQLite-only) | Engine uses `DatabaseInterface` (SQLite or PostgreSQL) |
| MCP had its own database connection | MCP reads from **same database** as Engine |
| Unclear who owns mutations | **Engine owns ALL writes**, MCP is read-only |
| Calendar synced to local DB | Calendar uses **API passthrough** (v4.2.0) |
| Embeddings generated ad-hoc | Engine generates embeddings automatically after sync |

### Data Flow

```
READ PATH (fast, local):
  MCP Tool → DatabaseInterface.get_*() → SQLite/PostgreSQL → Response

WRITE PATH (via Engine):
  MCP Tool → EngineClient.move_email() → Unix Socket → Engine API
           → ImapClient.move_email() → Gmail IMAP
           → DatabaseInterface.delete_email() → Database updated
```

## Component Responsibilities

| Component | Owns | Does NOT Do |
|-----------|------|-------------|
| **Engine** | IMAP connection, OAuth tokens, Calendar API, SMTP (send/draft), Database writes, Embedding generation | Serve MCP protocol, Handle AI client auth |
| **MCP Server** | MCP protocol, Bearer auth, Tool definitions, Database reads | IMAP connection, OAuth, Database writes, Send emails |

## Database Backends

Both Engine and MCP use `DatabaseInterface`, configured by `config.database.backend`:

### SQLite (Default)

```yaml
database:
  backend: sqlite
  sqlite:
    email_cache_path: config/email_cache.db
```

**Characteristics:**
- Single database file for email cache
- WAL mode for concurrent reads
- FTS5 for full-text search
- Zero external dependencies

### PostgreSQL + pgvector

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
    provider: openai
    model: text-embedding-3-small
    api_key: ${OPENAI_API_KEY}
```

**Characteristics:**
- Single database (unified schema)
- pgvector for semantic search
- Connection pooling
- HNSW index for fast similarity queries

## Engine Internal API

The Engine exposes a FastAPI server on Unix socket (`/tmp/secretary-engine.sock`):

### Status & Sync

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Health check, enrollment status, sync state |
| `/api/sync/trigger` | POST | Trigger immediate email + calendar sync |

### Email Mutations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/email/move` | POST | Move email to folder (IMAP + DB) |
| `/api/email/mark-read` | POST | Mark email as read |
| `/api/email/mark-unread` | POST | Mark email as unread |
| `/api/email/labels` | POST | Add/remove/set Gmail labels |
| `/api/email/send` | POST | Send email via Gmail API |
| `/api/email/draft-reply` | POST | Create draft reply in Gmail |
| `/api/email/setup-labels` | POST | Create Secretary label hierarchy |

### Calendar Operations (API Passthrough)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/calendar/events` | GET | List events in time range (direct API call) |
| `/api/calendar/availability` | GET | Get free/busy information |
| `/api/calendar/event` | POST | Create calendar event |
| `/api/calendar/list` | GET | List all calendars |
| `/api/calendar/{id}` | GET | Get calendar details |
| `/api/calendar/{id}/events/{event_id}` | GET | Get single event |
| `/api/calendar/{id}/events/{event_id}` | PATCH | Update event |
| `/api/calendar/{id}/events/{event_id}` | DELETE | Delete event |
| `/api/calendar/freebusy` | POST | Free/busy query |
| `/api/calendar/respond` | POST | Accept/decline/tentative meeting |

## Sync Strategy

### Email Sync (Engine)

```python
async def sync_emails():
    for folder in allowed_folders:
        # 1. Get last synced UID
        folder_state = database.get_folder_state(folder)
        last_uid = folder_state.get("uidnext", 1)
        
        # 2. Search for new emails (UID > last_uid)
        uids = imap_client.search({"uid_range": (last_uid, "*")}, folder)
        
        # 3. Fetch and store
        emails = imap_client.fetch_emails(uids, folder)
        for uid, email in emails.items():
            database.upsert_email(...)
        
        # 4. Update folder state
        database.save_folder_state(folder, uidvalidity, max_uid + 1)
```

### Calendar API (v4.2.0 - API Passthrough)

Calendar operations go directly to Google Calendar API without local caching:

```python
async def get_calendar_events():
    # Direct API call - no local database
    return calendar_client.list_events(
        time_min=time_min,
        time_max=time_max,
        calendar_id="primary"
    )
```

**Why no calendar caching?**
- Calendar dataset is small (hundreds of events vs 50k+ emails)
- Google Calendar API is fast enough for direct queries
- Removes sync complexity and staleness issues
- Events always reflect current state

### Embedding Generation (Engine, PostgreSQL only)

```python
async def generate_embeddings():
    if not database.supports_embeddings():
        return
    
    for folder in folders:
        emails = database.get_emails_needing_embedding(folder, limit=50)
        for email in emails:
            embedding = embeddings_client.embed_text(email.subject + email.body)
            database.upsert_embedding(email.uid, folder, embedding, model, hash)
```

## Graceful Startup

The Engine supports **graceful enrollment** - it starts even without OAuth tokens:

```
1. Engine starts → checks for OAuth tokens
2. No tokens? → Starts in "no_account" mode
   - API endpoints return {"status": "no_account", ...}
   - Enrollment watch loop monitors config/token.json
3. User runs auth_setup → tokens written to token.json
4. Engine detects change → auto-connects IMAP + Calendar
5. Sync loop starts → emails/calendar sync to database
6. MCP tools now work
```

## Database Schema

### Email Cache

```sql
CREATE TABLE emails (
    uid INTEGER,
    folder TEXT,
    message_id TEXT,
    gmail_thread_id BIGINT,      -- X-GM-THRID
    gmail_msgid BIGINT,          -- X-GM-MSGID
    gmail_labels JSONB,          -- Full Gmail label set
    subject TEXT,
    from_addr TEXT,
    to_addr TEXT,        -- JSON array
    cc_addr TEXT,        -- JSON array
    date TEXT,
    internal_date TEXT,  -- IMAP INTERNALDATE
    body_text TEXT,
    body_html TEXT,
    flags TEXT,          -- JSON array
    modseq BIGINT,       -- CONDSTORE sequence
    is_unread INTEGER,
    is_important INTEGER,
    size INTEGER,
    has_attachments INTEGER,
    attachment_filenames TEXT,  -- JSON array
    in_reply_to TEXT,
    references_header TEXT,
    PRIMARY KEY (uid, folder)
);

CREATE TABLE folder_state (
    folder TEXT PRIMARY KEY,
    uidvalidity INTEGER,
    uidnext INTEGER,
    highestmodseq INTEGER DEFAULT 0
);

-- SQLite FTS5 for full-text search
CREATE VIRTUAL TABLE emails_fts USING fts5(
    subject, body_text, from_addr, to_addr,
    content='emails', content_rowid='rowid'
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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (email_uid, email_folder),
    FOREIGN KEY (email_uid, email_folder) REFERENCES emails(uid, folder)
);

-- HNSW index for fast cosine similarity
CREATE INDEX idx_email_embeddings_hnsw 
ON email_embeddings USING hnsw (embedding vector_cosine_ops);
```

## Performance Characteristics

| Operation | SQLite | PostgreSQL |
|-----------|--------|------------|
| Email lookup by UID | <1ms | <5ms |
| Full-text search | 10-50ms (FTS5) | 5-20ms (GIN) |
| Semantic search | N/A | 20-100ms (HNSW) |
| Sync loop (incremental) | <1s | <1s |
| Database reads (MCP) | Direct file access | Connection pool |

## Deployment

### Single Container (Recommended)

Both processes run in one container via supervisord:

```yaml
services:
  secretary:
    image: ghcr.io/johnneerdael/gmail-secretary-mcp:4.2.0
    volumes:
      - ./config:/app/config
    ports:
      - "8000:8000"
    environment:
      - BEARER_TOKEN=${BEARER_TOKEN}
```

### Dual Container (Advanced)

Separate containers sharing Unix socket:

```yaml
services:
  engine:
    image: ghcr.io/johnneerdael/gmail-secretary-mcp:4.2.0
    command: ["python", "-m", "workspace_secretary.engine"]
    volumes:
      - ./config:/app/config
      - socket:/tmp

  mcp:
    image: ghcr.io/johnneerdael/gmail-secretary-mcp:4.2.0
    command: ["python", "-m", "workspace_secretary"]
    volumes:
      - ./config:/app/config:ro
      - socket:/tmp:ro
    ports:
      - "8000:8000"
    depends_on:
      - engine

volumes:
  socket:
```

## Migration from v3.x

**Automatic and seamless:**

1. Existing SQLite cache files are compatible
2. No config changes required (calendar_cache_path is ignored if present)
3. Engine will use existing `email_cache.db`
4. Calendar now uses API passthrough (no local cache needed)

## IMAP Client Deep Dive

The IMAP client is a core differentiator of Gmail Secretary. Rather than using the Gmail API (which has strict quotas and rate limits), we leverage Gmail's IMAP interface with advanced extensions for a high-performance, real-time email sync engine.

### Why IMAP over Gmail API?

| Aspect | Gmail API | IMAP (our approach) |
|--------|-----------|---------------------|
| **Rate limits** | 250 quota units/sec | Effectively unlimited |
| **Real-time updates** | Polling or Pub/Sub setup | Native IDLE push |
| **Bulk operations** | Multiple API calls | Single FETCH command |
| **Threading** | API call per thread | X-GM-THRID in FETCH |
| **Complexity** | OAuth + API client | OAuth + IMAP client |
| **Offline capability** | Requires caching layer | Built-in with local DB |

### IMAP Extensions Used

We leverage several IMAP extensions beyond RFC 3501:

#### CONDSTORE (RFC 7162)

Conditional STORE enables efficient incremental sync:

```imap
# Enable CONDSTORE on SELECT
A001 SELECT INBOX (CONDSTORE)
* OK [HIGHESTMODSEQ 123456789] Highest modseq

# Fetch only changes since last sync
A002 FETCH 1:* (FLAGS) (CHANGEDSINCE 123456780)
* 42 FETCH (FLAGS (\Seen) MODSEQ (123456785))
* 99 FETCH (FLAGS (\Flagged) MODSEQ (123456789))
```

**Benefits:**
- Only fetch emails with flag changes (not entire mailbox)
- Server tracks modification sequence per message
- Reduces bandwidth by 99%+ for incremental syncs

#### IDLE (RFC 2177)

Push notifications for real-time updates:

```imap
A003 IDLE
+ idling
* 100 EXISTS        # New message arrived!
* 42 FETCH (FLAGS (\Seen \Answered))  # Flags changed
DONE
A003 OK IDLE terminated
```

**Our implementation:**
- Dedicated IDLE connection per monitored folder
- Automatic reconnection on timeout (Gmail: 29 minutes)
- Triggers immediate sync on EXISTS/EXPUNGE/FETCH events

#### Gmail IMAP Extensions

Google provides proprietary extensions for Gmail-specific features:

**X-GM-THRID** - Thread ID:
```imap
A004 FETCH 1:10 (X-GM-THRID)
* 1 FETCH (X-GM-THRID 1278455344230334865)
```

**X-GM-MSGID** - Unique Message ID:
```imap
A005 FETCH 1 (X-GM-MSGID)
* 1 FETCH (X-GM-MSGID 1278455344230334866)
```

**X-GM-LABELS** - Gmail Labels:
```imap
A006 FETCH 1 (X-GM-LABELS)
* 1 FETCH (X-GM-LABELS ("\\Important" "Work" "Project-Alpha"))
```

**X-GM-RAW** - Gmail Search Syntax:
```imap
A007 SEARCH X-GM-RAW "from:boss@company.com has:attachment"
* SEARCH 5 12 89 234
```

### Sync Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    IMAP Sync Engine                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌─────────────┐  │
│  │ Main Client  │     │ IDLE Client  │     │ Reconnect   │  │
│  │              │     │              │     │ Manager     │  │
│  │ • Initial    │     │ • Push       │     │             │  │
│  │   sync       │     │   notifications│   │ • Exponential│ │
│  │ • Incremental│     │ • Per-folder │     │   backoff   │  │
│  │   updates    │     │   monitoring │     │ • Health    │  │
│  │ • CONDSTORE  │     │ • 29min      │     │   checks    │  │
│  │   deltas     │     │   keepalive  │     │             │  │
│  └──────┬───────┘     └──────┬───────┘     └──────┬──────┘  │
│         │                    │                     │         │
│         ▼                    ▼                     ▼         │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Connection Pool + OAuth2                   │ │
│  │  • Automatic token refresh                              │ │
│  │  • XOAUTH2 SASL mechanism                               │ │
│  │  • Connection reuse                                     │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Gmail IMAP    │
                    │ imap.gmail.com  │
                    │     :993        │
                    └─────────────────┘
```

### UIDNEXT Tracking

We use UIDNEXT for efficient new message detection:

```python
# On folder SELECT, Gmail returns:
# * OK [UIDNEXT 12345] Predicted next UID

# Our sync logic:
stored_uidnext = database.get_folder_state(folder).uidnext
if stored_uidnext:
    # Only fetch UIDs >= stored value
    new_uids = imap.search(f"UID {stored_uidnext}:*")
else:
    # Initial sync - fetch all
    new_uids = imap.search("ALL")

# After sync, store new UIDNEXT
database.save_folder_state(folder, uidnext=current_uidnext)
```

**Edge cases handled:**
- UIDVALIDITY changes (full re-sync required)
- Gaps in UID sequence (deleted messages)
- Server-side expunges during sync

### Batch Fetching Strategy

Large mailboxes require careful batching:

```python
BATCH_SIZE = 500  # Optimal for Gmail

def fetch_emails(uids: List[int], folder: str):
    results = {}
    for batch in chunks(uids, BATCH_SIZE):
        # Single FETCH for multiple attributes
        data = imap.fetch(
            batch,
            "(UID FLAGS INTERNALDATE RFC822.SIZE "
            "BODY.PEEK[HEADER] BODY.PEEK[TEXT] "
            "X-GM-THRID X-GM-MSGID X-GM-LABELS)"
        )
        results.update(data)
    return results
```

**Why 500?**
- Gmail handles up to ~1000 per FETCH
- 500 balances memory usage vs round-trips
- Allows progress logging every batch

### OAuth2 Authentication

We use XOAUTH2 SASL mechanism:

```python
def authenticate(self, access_token: str, email: str):
    # Build XOAUTH2 string
    auth_string = f"user={email}\x01auth=Bearer {access_token}\x01\x01"
    encoded = base64.b64encode(auth_string.encode()).decode()
    
    # IMAP AUTHENTICATE command
    self.connection.authenticate("XOAUTH2", lambda x: encoded)
```

**Token refresh flow:**
1. Engine detects 401/token expiry
2. Uses refresh_token to get new access_token
3. Updates token.json
4. Reconnects IMAP with new token
5. Resumes sync from last position

### Error Handling & Resilience

| Error | Recovery Strategy |
|-------|-------------------|
| Connection timeout | Exponential backoff (1s → 2s → 4s → ... → 60s max) |
| Token expired | Auto-refresh, reconnect |
| UIDVALIDITY changed | Full folder re-sync |
| Temporary Gmail error | Retry with backoff |
| Permanent error (e.g., folder deleted) | Log, skip folder, continue |

### Performance Metrics

| Metric | Typical Value |
|--------|---------------|
| Initial sync (10k emails) | 3-5 minutes |
| Incremental sync (idle) | < 500ms |
| IDLE notification latency | < 2 seconds |
| Memory per 10k emails | ~50MB during sync |
| CONDSTORE delta check | < 100ms |

### Feature Evolution

| Version | IMAP Enhancement |
|---------|------------------|
| v1.0 | Basic IMAP sync |
| v2.0 | IDLE push notifications |
| v3.0 | CONDSTORE incremental sync |
| v4.0 | Gmail extensions (X-GM-THRID, X-GM-LABELS) |
| v4.1 | OAuth2 auto-refresh, reconnect manager |
| v4.2 | UIDNEXT tracking, batch optimization |
