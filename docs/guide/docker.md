# Docker Deployment

This guide covers how to deploy and run the Google Workspace Secretary server using Docker. This is the recommended way to run the service for long-term usage.

## Prerequisites
- Docker and Docker Compose installed on your system.
- A `config.yaml` file prepared (see [Configuration](configuration.md)).

## Quick Start

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/johnneerdael/Google-Workspace-Secretary-MCP.git
    cd Google-Workspace-Secretary-MCP
    ```

2.  **Configure:**
    Copy `config.sample.yaml` to `config.yaml` and fill in your details.
    ```bash
    cp config.sample.yaml config.yaml
    ```

3.  **Start Service:**
    ```bash
    docker-compose up -d --build
    ```
    This starts the server in background mode. The service is configured to restart automatically (`restart: always`).

4.  **Verify:**
    ```bash
    docker-compose logs -f
    ```

## Persistence

The Docker container uses volumes to persist critical data. You don't need to rebuild the container to change configuration.

-   `./config.yaml` -> `/app/config/config.yaml`: Configuration file.
-   `./tasks.json` -> `/app/tasks.json`: Persistent tasks state (if using Task features).
-   `./.token_cache.json` -> `/app/.token_cache.json`: OAuth tokens are cached here automatically.

## Authentication in Docker

### The OAuth Redirect Issue
When running in Docker, `localhost` inside the container is different from your machine's `localhost`. The standard OAuth flow that opens a browser window won't work directly because the container can't launch your browser.

To authenticate:

1.  **Start Container**: Ensure the container is running (`docker-compose up -d`).
2.  **Run Auth Script Inside Container**:
    Execute the auth setup script *inside* the running container context:
    ```bash
    docker exec -it workspace-secretary uv run python -m workspace_secretary.auth_setup --config /app/config/config.yaml
    ```
3.  **Follow Instructions**:
    - The script will print a URL. Copy it to your browser.
    - Login to your Google account and approve access.
    - The browser will redirect to `localhost:8080`.
    - **Crucial**: We have mapped port 8080 of the container to port 8080 of your host. The container will capture this redirect and save the token to `config.yaml`.

4.  **Restart**:
    If the server was in a crash loop waiting for tokens, restart it now:
    ```bash
    docker-compose restart
    ```

## Environment Variables

You can override defaults in `docker-compose.yml` or using a `.env` file:

-   `IMAP_MCP_TOKEN`: Set a fixed Bearer token for MCP client authentication.
    -   *Default*: Generated randomly on startup (check logs to see it).
-   `LOG_LEVEL`: Set logging verbosity (e.g., `DEBUG`, `INFO`).

## Connecting Clients

Once running, the server exposes a **Streamable HTTP** endpoint at:
`http://localhost:8000/mcp`

See the [Client Setup Guide](clients.md) for instructions on connecting Claude Desktop, VS Code, and other tools.
