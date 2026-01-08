# Google Workspace Secretary MCP

Google Workspace Secretary MCP is an AI-native Model Context Protocol (MCP) server that transforms your Google Workspace (Gmail, Calendar) and email inboxes into a searchable, programmable knowledge base for Claude and other AI assistants.

[📚 View Full Documentation](https://johnneerdael.github.io/Google-Workspace-Secretary-MCP/)

## 🚀 Overview

The Google Workspace Secretary MCP server enables AI assistants to act as intelligent email and calendar secretaries. Unlike simple email clients, this server is optimized for high-density AI analysis, document processing, and advanced calendar management with **timezone-aware scheduling** and **intelligent email prioritization**.

### Key Capabilities
- **Intelligent Triage**: Discovery of new work with priority signals (VIPs, questions, deadlines).
- **Timezone-Aware Scheduling**: All calendar operations respect your configured timezone and working hours.
- **Document Intelligence**: Deep-dive into attachments (PDF, DOCX) directly into the AI's context.
- **Safe Actions**: "Draft First" philosophy ensures AI never sends emails without your approval.

## ⚡ Quick Start

### 1. Run with Docker (Recommended)

```bash
# Clone the repo
git clone https://github.com/johnneerdael/Google-Workspace-Secretary-MCP.git
cd Google-Workspace-Secretary-MCP

# Create config
cp config.sample.yaml config.yaml
# (Edit config.yaml with your details)

# Start server
docker-compose up -d
```

### 2. Connect your Client

The server exposes a **Streamable HTTP** endpoint at:
`http://localhost:8000/mcp`

Configure your client (Claude Desktop, VS Code, etc.) to connect to this URL.
See the [Client Setup Guide](https://johnneerdael.github.io/Google-Workspace-Secretary-MCP/guide/clients.html) for detailed instructions.

## 🛠️ Configuration

See [Configuration Guide](https://johnneerdael.github.io/Google-Workspace-Secretary-MCP/guide/configuration.html) for full details on `config.yaml` options.

## 🤖 AI Usage Examples

Once connected, you can ask your AI assistant to perform complex workflows:

- **Daily Briefing**: "Give me my daily briefing - what emails need my attention today?"
- **Intelligent Triage**: "Scan my last 20 unread emails. Prioritize any from VIPs or urgent requests."
- **Smart Scheduling**: "I received a meeting invite from John. Check my calendar and if I'm free, draft an acceptance."

## 📚 Documentation

Full documentation is available at:
[https://johnneerdael.github.io/Google-Workspace-Secretary-MCP/](https://johnneerdael.github.io/Google-Workspace-Secretary-MCP/)

- [Installation & Docker](https://johnneerdael.github.io/Google-Workspace-Secretary-MCP/guide/docker.html)
- [Client Setup](https://johnneerdael.github.io/Google-Workspace-Secretary-MCP/guide/clients.html)
- [Agent Workflows](https://johnneerdael.github.io/Google-Workspace-Secretary-MCP/guide/agents.html)

---

Built with the [Model Context Protocol](https://modelcontextprotocol.io/)

GitHub: [https://github.com/johnneerdael/Google-Workspace-Secretary-MCP](https://github.com/johnneerdael/Google-Workspace-Secretary-MCP)
