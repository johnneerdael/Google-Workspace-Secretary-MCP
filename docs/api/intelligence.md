# Intelligence Tools

Smart analysis and prioritization tools.

## get_daily_briefing

Combined calendar + email intelligence for a given day.

**Parameters:**
- `date` (string, required): ISO date (YYYY-MM-DD)

**Returns:**
```json
{
  "date": "2026-01-09",
  "timezone": "America/Los_Angeles",
  "calendar_events": [...],
  "email_candidates": [
    {
      "subject": "...",
      "from": "...",
      "date": "...",
      "snippet": "...",
      "signals": {
        "is_from_vip": true,
        "is_important": false,
        "has_question": true,
        "mentions_deadline": false,
        "mentions_meeting": true
      }
    }
  ]
}
```

**Signals:**
- `is_from_vip`: Sender in configured `vip_senders`
- `is_important`: Gmail IMPORTANT label
- `has_question`: Contains `?` or polite requests
- `mentions_deadline`: Keywords like EOD, ASAP, urgent
- `mentions_meeting`: Keywords like meet, schedule, zoom

**AI should decide priority** based on these signals + context.

## summarize_thread

Get structured summary of email thread.

**Parameters:**
- `thread_id` (string, required): Gmail thread ID

**Returns:**
- `participants`: List of all senders/recipients
- `key_points`: Extracted discussion points
- `action_items`: Detected tasks/requests
- `latest_message`: Most recent message

## More Tools

See full tool list in the [README](https://github.com/johnneerdael/Google-Workspace-Secretary-MCP#-available-tools).
