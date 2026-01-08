# API Reference

Complete reference for all Google Workspace Secretary MCP tools.

## Tool Categories

The server provides tools organized by function:

- [Email & Search Tools](./email) - Read, search, and analyze emails
- [Calendar Tools](./calendar) - Manage calendar events and availability  
- [Intelligence Tools](./intelligence) - Daily briefings and smart prioritization

## Quick Reference

### Email Operations

| Tool | Purpose |
|------|---------|
| `get_unread_messages` | Fetch recent unread emails |
| `search_emails` | Search with keywords or advanced criteria |
| `get_email_details` | Get full email content + attachments |
| `get_thread` | Retrieve entire conversation thread |

### Calendar Operations

| Tool | Purpose |
|------|---------|
| `check_calendar` | Check availability in time range |
| `suggest_reschedule` | Find alternative meeting times |
| `list_calendar_events` | List events in date range |

### Intelligence

| Tool | Purpose |
|------|---------|
| `get_daily_briefing` | Combined calendar + email intelligence |
| `summarize_thread` | AI-friendly thread summary |

## Tool Response Format

All tools return JSON with:
- `content`: Array of text/data responses
- `isError`: Boolean indicating success/failure

**Example successful response:**
```json
{
  "content": [
    {
      "type": "text",
      "text": "Found 5 unread emails..."
    }
  ],
  "isError": false
}
```

**Example error response:**
```json
{
  "content": [
    {
      "type": "text",
      "text": "Error: Invalid folder name"
    }
  ],
  "isError": true
}
```

## Authentication

Tools automatically use the configured authentication (OAuth2 or password) from `config.yaml`.

## Rate Limits

- Gmail API: 250 quota units/second/user (see [Gmail API quotas](https://developers.google.com/gmail/api/reference/quota))
- Calendar API: 500 queries/second/user

The server does not implement rate limiting internally; rely on Google's limits.

## Next Steps

- [Email Tools Reference](./email) - Detailed email tool documentation
- [Calendar Tools Reference](./calendar) - Detailed calendar tool documentation
- [Intelligence Tools Reference](./intelligence) - Briefing and analysis tools
