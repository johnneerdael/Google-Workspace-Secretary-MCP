---
layout: home

hero:
  name: "Google Workspace Secretary"
  text: "AI-Native MCP Server"
  tagline: Transform Gmail and Google Calendar into an intelligent, AI-powered knowledge base
  image:
    src: /hero-image.svg
    alt: Google Workspace Secretary MCP
  actions:
    - theme: brand
      text: Get Started
      link: /getting-started
    - theme: alt
      text: View on GitHub
      link: https://github.com/johnneerdael/Google-Workspace-Secretary-MCP

features:
  - icon: 🤖
    title: AI-Native Design
    details: Built specifically for AI assistants like Claude via Model Context Protocol (MCP). Provides intelligent tools that scaffold complex email and calendar workflows.
    
  - icon: 🧠
    title: Intelligent Prioritization
    details: Daily briefings with ML-ready signals for VIP senders, urgency markers, questions, and deadlines. The AI decides priority based on your context.
    
  - icon: 🌍
    title: Timezone-Aware Scheduling
    details: All calendar operations respect your configured timezone and working hours. Automatically suggests meeting times that fit your schedule.
    
  - icon: 📧
    title: Advanced Email Processing
    details: Bulk triage with token-efficient truncation, full thread analysis, and natural language search across your entire inbox history.
    
  - icon: 📄
    title: Document Intelligence
    details: Extract and analyze text from PDF, DOCX, TXT, and LOG attachments directly in the AI's context. No manual downloads needed.
    
  - icon: 🔒
    title: Human-in-the-Loop Safety
    details: Built-in safety patterns ensure all mutations (sending emails, deleting, moving) require explicit user confirmation.
    
  - icon: 📅
    title: Calendar Orchestration
    details: Check availability, parse meeting invites, and draft professional responses. All within your working hours and timezone.
    
  - icon: 🐳
    title: Production-Ready
    details: Docker images published on every release. OAuth2 support, environment variable configuration, and comprehensive logging.
---

## Quick Start

Install via Docker (recommended):

```yaml
# docker-compose.yml
services:
  workspace-secretary:
    image: ghcr.io/johnneerdael/google-workspace-secretary-mcp:latest
    ports:
      - "8000:8000"
    volumes:
      - ./config.yaml:/app/config/config.yaml
      - ./credentials.json:/app/credentials.json
    environment:
      - WORKSPACE_TIMEZONE=America/Los_Angeles
      - WORKING_HOURS_START=09:00
      - WORKING_HOURS_END=17:00
      - VIP_SENDERS=boss@company.com,ceo@company.com
    restart: always
```

Then start with: `docker-compose up -d`

See [Getting Started](/getting-started) for complete installation instructions.

## Why Google Workspace Secretary MCP?

Traditional email clients are built for humans. **Google Workspace Secretary MCP** is built for AI assistants.

- **Token-efficient**: Bulk email fetching with smart truncation (700 chars) for fast triage
- **Context-rich**: Full thread history, attachment content, and calendar context in one tool call
- **Intelligence signals**: VIP detection, urgency markers, question detection—not hardcoded decisions
- **Agentic workflows**: Compose specialized agents (Triage, Scheduler, Intelligence Clerk) using atomic tools

## Example Workflows

::: tip Daily Briefing
"Give me my daily briefing—what emails need my attention today?"

The AI uses `get_daily_briefing()` to fetch:
- Today's calendar events
- Email candidates with 5 priority signals (VIP, urgent, questions, deadlines, meetings)
- Intelligent summary prioritizing your VIP senders and time-sensitive requests
:::

::: tip Smart Scheduling
"I received a meeting invite from John for tomorrow at 2 PM. Check my calendar and if I'm free during working hours, draft an acceptance."

The AI:
1. Checks calendar availability with `check_calendar()`
2. Validates time is within your `working_hours`
3. Uses `create_draft_reply()` to prepare response
4. Shows you the draft for confirmation
:::

::: tip Document Intelligence
"Find the invoice PDF sent by Accounting last week, read it, and tell me the total amount."

The AI:
1. Searches with `search_emails(keyword='invoice', from='accounting')`
2. Extracts PDF text with `get_attachment_content()`
3. Parses and presents the total
:::

## What's New in v0.2.0

- ✅ **Timezone-aware scheduling** - All calendar operations use your configured timezone
- ✅ **Working hours constraints** - Meeting suggestions respect your work schedule
- ✅ **Intelligent email signals** - 5 ML-ready signals for AI-driven prioritization
- ✅ **VIP sender detection** - Configurable list of priority email addresses
- ✅ **Enhanced daily briefings** - Combined calendar + email intelligence in one call
- ✅ **Environment variable support** - Easy configuration via Docker ENV vars

[See Migration Guide](/guide/configuration#migration-from-v01x) for upgrading from v0.1.x.

## Community & Support

- [GitHub Repository](https://github.com/johnneerdael/Google-Workspace-Secretary-MCP)
- [Report Issues](https://github.com/johnneerdael/Google-Workspace-Secretary-MCP/issues)
- [View Releases](https://github.com/johnneerdael/Google-Workspace-Secretary-MCP/releases)

---

<div style="text-align: center; margin-top: 40px; color: var(--vp-c-text-2);">
  <p>Built with ❤️ for the AI-native future</p>
  <p style="font-size: 14px;">Licensed under MIT • © 2024-present John Neerdael</p>
</div>
