# Guide

Welcome to the Google Workspace Secretary MCP Guide. This section covers everything you need to know to configure, deploy, and use the server effectively.

## Getting Started

New to Google Workspace Secretary MCP? Start here:

- [Installation](/getting-started) - Set up the server with Docker or locally
- [Configuration](./configuration) - Configure timezone, working hours, and VIP senders
- [Docker Deployment](./docker) - Production Docker setup

## Building AI Agents

Learn how to build intelligent secretaries:

- [Agent Patterns](./agents) - Learn the Morning Briefing Agent, Triage Agent, Scheduling Agent, and Intelligence Clerk patterns
- [Use Cases](./use-cases) - Real-world examples and workflows

## Core Concepts

### The Human-in-the-Loop (HITL) Pattern

All mutation operations (send email, delete, move) **require explicit user confirmation**. The server provides tools to *prepare* actions (like `create_draft_reply`) but execution tools require the user to review and approve.

### Intelligence Signals, Not Decisions

Tools provide **signals** for the AI to interpret:
- `is_from_vip`: Email is from a configured VIP sender
- `mentions_deadline`: Contains urgency keywords (EOD, ASAP, urgent)
- `has_question`: Contains questions or polite requests
- `is_important`: Gmail's IMPORTANT label
- `mentions_meeting`: Contains meeting-related keywords

The **AI decides priority** based on context, not the tool.

### Timezone-Aware Operations

All calendar operations respect your configured:
- `timezone`: IANA timezone (e.g., `America/Los_Angeles`)
- `working_hours`: Start/end times and workdays (1=Monday, 7=Sunday)

Meeting suggestions only occur within your working hours.

## Quick Reference

### Configuration Fields

| Field | Required | Description |
|-------|----------|-------------|
| `imap.host` | ✅ | IMAP server (e.g., `imap.gmail.com`) |
| `imap.username` | ✅ | Email address |
| `timezone` | ✅ | IANA timezone string |
| `working_hours` | ✅ | Start, end, workdays |
| `vip_senders` | ✅ | List of priority email addresses |
| `calendar.enabled` | ❌ | Enable calendar tools (default: `false`) |
| `allowed_folders` | ❌ | Restrict folder access |

See [Configuration](./configuration) for details.

### Common Tasks

- **Daily Briefing**: Ask AI "Give me my daily briefing"
- **Triage Emails**: "Scan my last 20 unread emails and prioritize VIPs"
- **Schedule Meeting**: "Check if I'm free tomorrow at 2 PM"
- **Find Document**: "Find the invoice PDF from Accounting"
- **Draft Reply**: "Draft a polite reply saying I'll review by EOD"

## Next Steps

1. [Configure your server](./configuration) with timezone and VIP senders
2. Learn [Agent Patterns](./agents) to build specialized workflows
3. Explore the [API Reference](/api/) for all available tools

---

**Questions?** Check out [Use Cases](./use-cases) or [open an issue](https://github.com/johnneerdael/Google-Workspace-Secretary-MCP/issues).
