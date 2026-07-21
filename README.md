# vane-mcp-server

**Vane MCP Server** — Model Context Protocol server for the [Vane](https://github.com/ItzCrazyKns/Vane) AI Search Engine.

Connects the Vane AI search engine as a set of MCP tools to any MCP client:
Claude Desktop, Cursor, OpenCode, Continue, Windsurf, and others.

## ✨ Features

- 🔍 **web_search** — fast web search with AI answer (speed mode)
- 🔬 **deep_research** — in-depth research with dozens of sources (quality mode)
- ⚖️ **balanced_search** — balanced search for most queries
- 📰 **search_news** — news and discussion search (web + social)
- 📊 **vane://status** — MCP resource for health monitoring

## 🏗️ Architecture

```
┌─────────────────┐     MCP (stdio/SSE)     ┌──────────────────┐
│  MCP Client     │ ◄──────────────────────► │  Vane MCP Server │
│  (Claude,       │                          │  (Python/FastMCP)│
│   Cursor,       │                          └────────┬─────────┘
│   OpenCode...)  │                                   │ HTTP
└─────────────────┘                          ┌────────▼─────────┐
                                              │  Vane API        │
                                              │  (VANE_BASE_URL) │
                                              └────────┬─────────┘
                                                       │
                                              ┌────────▼─────────┐
                                              │  SearxNG         │
                                              │  (localhost:8080)│
                                              └────────┬─────────┘
                                                       │
                                              ┌────────▼─────────┐
                                              │  FlareSolverr    │
                                              │  (localhost:8191)│
                                              └────────┬─────────┘
                                                       │
                                              ┌────────▼─────────┐
                                              │  OpenAI-compatible│
                                              │  LLM API          │
                                              └──────────────────┘
```

## 📋 Requirements

- Python 3.11+
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- An OpenAI-compatible LLM API endpoint (e.g., OpenAI, DeepSeek, local LLM)

## 🚀 Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/YOUR_USER/vane-mcp-server.git
cd vane-mcp-server

# Run the setup script (checks Python, installs uv, installs the package)
./setup.sh

# Or install manually:
uv pip install -e .
# Or with pip:
# pip install -e .
```

### 2. Start Vane, SearxNG, and FlareSolverr (Docker)

The repository includes a [`docker-compose.yml`](docker-compose.yml) that sets up:

- **Vane** — AI-powered answering engine (port 3000)
- **SearXNG** — meta-search engine (port 8080)
- **Valkey** — Redis-compatible cache for bot protection and rate limiting
- **FlareSolverr** — Cloudflare bypass proxy (port 8191)

```bash
# Start all services
docker compose up -d

# Verify they're running
docker compose ps

# Check Vane logs
docker compose logs -f vane
```

The SearxNG configuration is in [`searxng/settings.yml`](searxng/settings.yml).

#### Vane Configuration

Vane's own configuration (LLM API keys, model endpoints, etc.) is set inside the
Vane Docker container through environment variables in [`docker-compose.yml`](docker-compose.yml):

```yaml
vane:
  image: itzcrazykns1337/vane:slim-latest
  environment:
    - SEARXNG_API_URL=http://searxng:8080
    # Configure your LLM provider here (OpenAI-compatible endpoint)
    # - OPENAI_API_KEY=your-api-key
    # - MODEL_PROVIDER=openai
    # - OPENAI_API_BASE_URL=https://api.openai.com/v1
```

#### Finding Provider IDs and Model Keys

Once Vane is running, you can find the available provider IDs and model keys:

```bash
curl http://localhost:3000/api/providers
```

Provider IDs are UUIDs (e.g., `bb877f6f-a8a4-47e8-8381-fcb3812401a1`).
Model keys are the model names (e.g., `GLM-5.1`).

### 3. Connect to an MCP Client

All configuration is passed via environment variables in the MCP client's config file.
Example configuration files are provided in the [`config/`](config/) directory:

- [`config/claude_desktop.json`](config/claude_desktop.json) — for Claude Desktop
- [`config/cursor.json`](config/cursor.json) — for Cursor
- [`config/opencode.json`](config/opencode.json) — for OpenCode

Add the configuration to your MCP client's config file. Replace the provider IDs
and model keys with the values from your Vane instance.

#### Claude Desktop Example

```json
{
  "mcpServers": {
    "vane": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/vane-mcp-server",
        "vane-mcp"
      ],
      "env": {
        "VANE_BASE_URL": "http://localhost:3000",
        "VANE_CHAT_PROVIDER_ID": "bb877f6f-a8a4-47e8-8381-fcb3812401a1",
        "VANE_CHAT_MODEL_KEY": "GLM-5.1",
        "VANE_EMBEDDING_PROVIDER_ID": "020df018-9b5d-4afb-97bf-2a3330a01e43",
        "VANE_EMBEDDING_MODEL_KEY": "Qwen/Qwen3-VL-Embedding-2B"
      }
    }
  }
}
```

## 🔧 Environment Variables

All configuration is done through environment variables, passed to the MCP server
via the MCP client's `env` section.

| Variable | Required | Example | Description |
|---|---|---|---|
| `VANE_BASE_URL` | Yes | `http://localhost:3000` | The URL where your Vane instance is running |
| `VANE_CHAT_PROVIDER_ID` | Yes | `bb877f6f-a8a4-47e8-8381-fcb3812401a1` | UUID of the chat provider configured in Vane |
| `VANE_CHAT_MODEL_KEY` | Yes | `GLM-5.1` | The model key your chat provider uses |
| `VANE_EMBEDDING_PROVIDER_ID` | Yes | `020df018-9b5d-4afb-97bf-2a3330a01e43` | UUID of the embedding provider configured in Vane |
| `VANE_EMBEDDING_MODEL_KEY` | Yes | `Qwen/Qwen3-VL-Embedding-2B` | The model key your embedding provider uses |
| `VANE_API_KEY` | No | `sk-...` | API key for Vane (if your Vane instance requires authentication) |

> **Finding Provider IDs and Model Keys:**
> Run `curl http://localhost:3000/api/providers` to list all available
> providers and their model keys from your Vane instance.
> Provider IDs are UUIDs (e.g., `bb877f6f-a8a4-47e8-8381-fcb3812401a1`).
> Model keys are the model names (e.g., `GLM-5.1`).

## 📂 Project Structure

```
vane-mcp-server/
├── README.md                   # ← you are here
├── pyproject.toml              # Python project configuration
├── setup.sh                    # One-click installation script
├── docker-compose.yml          # Docker setup for Vane, SearxNG, Valkey, FlareSolverr
├── LICENSE                     # MIT
├── .gitignore
├── config/
│   ├── claude_desktop.json     # Example config for Claude Desktop
│   ├── opencode.json           # Example config for OpenCode
│   └── cursor.json             # Example config for Cursor
├── searxng/
│   └── settings.yml            # SearxNG configuration
└── src/
    └── vane_mcp/
        ├── __init__.py          # Version and metadata
        ├── server.py            # MCP server (FastMCP)
        └── client.py            # Async HTTP client for Vane API
```

## 🛠️ MCP Tools

### web_search

Fast web search with AI answer (speed mode).
Use for quick facts, current events, prices, news.

```
query: str — natural language search query
→ str — AI answer with source links
```

### balanced_search

Balanced search — the sweet spot between speed and depth.
For most search queries.

```
query: str → str
```

### deep_research

In-depth research with multiple sources (quality mode).
For complex questions requiring comprehensive analysis.

```
query: str → str
```

### search_news

Search news and discussions in social media.
Uses web + social sources.

```
query: str → str
```

## 🧪 Testing

```bash
# Check that the server imports correctly
python -c "from vane_mcp.server import mcp; print('OK')"

# Check that Vane is running and list available providers
curl http://localhost:3000/api/providers

# Check that SearxNG is accessible (JSON format)
curl -s "http://localhost:8080/search?q=test&format=json" | head -c 200

# Check that FlareSolverr is accessible
curl -s -X POST http://localhost:8191/v1 \
  -H 'Content-Type: application/json' \
  -d '{"cmd":"request.get","url":"http://www.google.com/","maxTimeout":60000}' | head -c 200
```

## 🔒 Security Considerations

- **Never expose FlareSolverr to the internet** — it can be abused.
- Always bind FlareSolverr to `127.0.0.1` or keep it within the Docker internal network.
- Change SearxNG's `secret_key` from the default value in production.
- If exposing SearXNG publicly, set up a reverse proxy (e.g., Caddy, Nginx) with TLS.
- Use access tokens for command-line engines to prevent exposure of sensitive information.

## 📝 License

MIT © 2026

## 🔗 Links

- [Vane GitHub](https://github.com/ItzCrazyKns/Vane)
- [SearXNG Documentation](https://docs.searxng.org/)
- [FlareSolverr GitHub](https://github.com/FlareSolverr/FlareSolverr)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [FastMCP](https://github.com/jlowin/fastmcp)
