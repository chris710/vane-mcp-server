# vane-mcp-server

**Vane MCP Server** — Model Context Protocol сервер для [Vane](https://github.com/ItzCrazyKns/Vane) AI Search Engine.

Подключает AI-поисковик Vane как набор MCP-инструментов к любому MCP-клиенту:
Claude Desktop, Cursor, OpenCode, Continue, Windsurf, и другим.

## ✨ Возможности

- 🔍 **web_search** — быстрый веб-поиск с AI-ответом (speed mode)
- 🔬 **deep_research** — глубокое исследование с десятками источников (quality mode)
- ⚖️ **balanced_search** — сбалансированный поиск для большинства запросов
- 📰 **search_news** — поиск новостей и обсуждений (web + social)
- 📊 **vane://status** — MCP-ресурс с мониторингом состояния

## 🏗️ Архитектура

```
┌─────────────────┐     MCP (stdio/SSE)     ┌──────────────────┐
│  MCP Client     │ ◄──────────────────────► │  Vane MCP Server │
│  (Claude,       │                          │  (Python/FastMCP)│
│   Cursor,       │                          └────────┬─────────┘
│   OpenCode...)  │                                   │ HTTP
└─────────────────┘                          ┌────────▼─────────┐
                                             │  Vane API        │
                                             │  (localhost:3000)│
                                             └────────┬─────────┘
                                                      │
                                             ┌────────▼─────────┐
                                             │  SearxNG         │
                                             │  (localhost:8080)│
                                             └────────┬─────────┘
                                                      │
                                             ┌────────▼─────────┐
                                             │  DeepSeek V4 Pro │
                                             │  (API)           │
                                             └──────────────────┘
```

## 📋 Требования

- Python 3.11+
- [Vane](https://github.com/ItzCrazyKns/Vane) запущенный на `localhost:3000`
- [SearxNG](https://github.com/searxng/searxng) запущенный на `localhost:8080`
- DeepSeek V4 Pro API ключ (или любой OpenAI-совместимый провайдер)

## 🚀 Быстрый старт

### 1. Установка

```bash
git clone https://github.com/YOUR_USER/vane-mcp-server.git
cd vane-mcp-server
./setup.sh
```

Или вручную:

```bash
pip install mcp httpx
pip install -e .
```

### 2. Запуск Vane и SearxNG

Перед использованием MCP-сервера, убедись что Vane и SearxNG запущены:

```bash
# SearxNG (Docker)
docker run -d --name searxng -p 8080:8080 searxng/searxng

# Vane (из исходников)
cd /path/to/Vane
npm install --legacy-peer-deps
npm run build
npm run start
```

Vane должен быть настроен с DeepSeek V4 Pro как OpenAI-провайдер.

### 3. Запуск MCP-сервера

**Stdio режим** (для локальных MCP-клиентов):

```bash
vane-mcp
# или
uv run vane-mcp
```

**SSE режим** (для удалённых клиентов):

```bash
vane-mcp --sse --port 8053
```

### 4. Подключение к MCP-клиенту

Добавь в конфиг своего MCP-клиента:

#### Claude Desktop

```json
{
  "mcpServers": {
    "vane": {
      "command": "uv",
      "args": ["run", "vane-mcp"],
      "env": {
        "VANE_BASE_URL": "http://localhost:3000"
      }
    }
  }
}
```

#### OpenCode / Cursor

```json
{
  "mcpServers": {
    "vane": {
      "command": "uvx",
      "args": ["vane-mcp"],
      "env": {
        "VANE_BASE_URL": "http://localhost:3000"
      }
    }
  }
}
```

#### Continue (VS Code)

```json
{
  "experimental": {
    "mcpServers": {
      "vane": {
        "command": "uvx",
        "args": ["vane-mcp"],
        "env": {
          "VANE_BASE_URL": "http://localhost:3000"
        }
      }
    }
  }
}
```

## 🔧 Переменные окружения

| Переменная | По умолчанию | Описание |
|---|---|---|
| `VANE_BASE_URL` | `http://localhost:3000` | URL Vane API |
| `VANE_CHAT_PROVIDER_ID` | `deepseek` | ID чат-провайдера в Vane |
| `VANE_CHAT_MODEL_KEY` | `deepseek-v4-pro` | Ключ модели чата |
| `VANE_EMBEDDING_PROVIDER_ID` | авто | ID провайдера эмбеддингов |
| `VANE_EMBEDDING_MODEL_KEY` | `Xenova/all-MiniLM-L6-v2` | Ключ модели эмбеддингов |

## 📂 Структура проекта

```
vane-mcp-server/
├── README.md                   # ← ты здесь
├── pyproject.toml              # Python проект
├── setup.sh                    # One-click установка
├── LICENSE                     # MIT
├── .gitignore
├── config/
│   ├── mcp.json                # Пример конфига для Claude Desktop
│   ├── opencode.json           # Пример конфига для OpenCode
│   └── cursor.json             # Пример конфига для Cursor
└── src/
    └── vane_mcp/
        ├── __init__.py          # Версия и метаданные
        ├── server.py            # MCP сервер (FastMCP)
        └── client.py            # Async HTTP клиент для Vane API
```

## 🛠️ Инструменты MCP

### web_search
Быстрый веб-поиск. Для фактов, цен, новостей, текущих событий.

```
query: str — поисковый запрос
→ str — AI-ответ + источники
```

### balanced_search
Сбалансированный поиск. Золотая середина для большинства запросов.

```
query: str → str
```

### deep_research
Глубокое исследование. Десятки источников, всесторонний анализ.

```
query: str → str
```

### search_news
Поиск новостей и обсуждений (web + social источники).

```
query: str → str
```

## 🧪 Тестирование

```bash
# Проверить что сервер импортируется
python -c "from vane_mcp.server import mcp; print('OK')"

# Проверить что Vane доступен
curl -s http://localhost:3000/api/search -X POST \
  -H 'Content-Type: application/json' \
  -d '{"query":"test","sources":["web"],"optimizationMode":"speed",...}'
```

## 📝 Лицензия

MIT © 2026

## 🔗 Ссылки

- [Vane GitHub](https://github.com/ItzCrazyKns/Vane)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [DeepSeek API](https://api-docs.deepseek.com/)
