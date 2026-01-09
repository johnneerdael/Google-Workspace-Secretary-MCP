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
        "is_addressed_to_me": true,
                        "mentions_my_name": false,
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
- `is_addressed_to_me`: User's email is in To: field
- `mentions_my_name`: User's full name mentioned in body
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

## quick_clean_inbox

Automatically clean inbox by moving emails where user is not directly addressed.

**Parameters:**
- `batch_size` (number, optional): Emails per batch (default: 20)

**Returns:**
```json
{
  "status": "success",
  "total_processed": 45,
  "moved": 12,
  "skipped": 33,
  "target_folder": "Secretary/Auto-Cleaned",
  "moved_emails": [{"uid": "123", "from": "...", "subject": "..."}],
  "skipped_emails": [{"uid": "456", "from": "...", "subject": "..."}]
}
```

**Safety Guarantees:**
- Only moves emails where user is NOT in To: or CC: fields
- Only moves emails where user's email/name is NOT in body
- Emails moved to `Secretary/Auto-Cleaned` (recoverable)
- Each email checked exactly once (no loops)

::: warning UNIQUE: No Confirmation Required
This is the **only mutation tool** that does not require user confirmation per AGENTS.md. The safety conditions are deterministic—if both fail, the email is provably not directed at the user.
:::

## triage_priority_emails

Identify high-priority emails for immediate attention.

**Parameters:**
- `batch_size` (number, optional): Emails per batch (default: 20)

**Priority Criteria:**
1. User in To: field with <5 total recipients, OR
2. User in To: field with <15 recipients AND first/last name in body

**Returns:**
```json
{
  "status": "success",
  "total_processed": 45,
  "priority_count": 8,
  "skipped_count": 37,
  "target_folder": "Secretary/Priority",
  "priority_emails": [
    {
      "uid": "123",
      "from": "boss@company.com",
      "subject": "Quick question",
      "date": "2026-01-09T10:30:00",
      "to_count": 2,
      "snippet": "...",
      "priority_reason": "direct_small_group (2 recipients)"
    }
  ],
  "next_action": "Delegate priority_emails to triage subagent"
}
```

::: tip Subagent Handoff
Results should be delegated to a triage subagent for content analysis and action determination.
:::

## triage_remaining_emails

Process emails that don't match auto-clean or high-priority criteria.

**Parameters:**
- `batch_size` (number, optional): Emails per batch (default: 20)

**Targets emails where:**
- User IS in To: or CC: (not auto-cleanable)
- Does NOT meet high-priority criteria

**Returns:**
```json
{
  "status": "success",
  "total_processed": 45,
  "remaining_count": 15,
  "target_folder": "Secretary/Waiting",
  "remaining_emails": [
    {
      "uid": "456",
      "from": "team@company.com",
      "subject": "FYI: Update",
      "user_in_to": false,
      "user_in_cc": true,
      "snippet": "...",
      "signals": {
        "is_from_vip": false,
        "name_mentioned": false,
        "has_question": false,
        "mentions_deadline": false
      }
    }
  ],
  "next_action": "Delegate remaining_emails to triage subagent"
}
```

## More Tools

See full tool list in the [README](https://github.com/johnneerdael/Google-Workspace-Secretary-MCP#-available-tools).
