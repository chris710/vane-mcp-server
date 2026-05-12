#!/usr/bin/env python3
"""
Vane MCP Server — Model Context Protocol сервер для Vane AI Search Engine.

Подключает Vane как набор инструментов к любому MCP-клиенту:
- Claude Desktop, Cursor, OpenCode, Continue, Windsurf, etc.

Архитектура:
    MCP Client ──(stdio/SSE)──> VaneMCPServer ──(HTTP)──> Vane API (localhost:3000)
                                                               │
                                                          SearxNG (localhost:8080)
                                                               │
                                                          DeepSeek V4 Pro API

Инструменты (tools):
    web_search      — быстрый веб-поиск (speed mode)
    deep_research   — глубокое исследование (quality mode)
    balanced_search — сбалансированный поиск (balanced mode)

Использование:
    uv run vane-mcp                   # stdio режим (для Claude Desktop, OpenCode)
    uv run vane-mcp --sse --port 8053 # SSE режим (для удалённых клиентов)

Зависимости:
    mcp>=1.14.0, httpx>=0.28.0
"""

import os
import sys
import json
import logging
import argparse
from typing import Optional, Any
from contextlib import asynccontextmanager

import httpx
from mcp.server.fastmcp import FastMCP, Context
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

from vane_mcp.client import VaneClient, SearchResult
from vane_mcp import __version__

# ── Logging ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [vane-mcp] %(levelname)s %(message)s",
)
logger = logging.getLogger("vane-mcp")

# ── Config ───────────────────────────────────────────────
VANE_BASE_URL = os.getenv("VANE_BASE_URL", "http://localhost:3000")
CHAT_PROVIDER_ID = os.getenv("VANE_CHAT_PROVIDER_ID", "deepseek")
CHAT_MODEL_KEY = os.getenv("VANE_CHAT_MODEL_KEY", "deepseek-v4-pro")
EMBEDDING_PROVIDER_ID = os.getenv(
    "VANE_EMBEDDING_PROVIDER_ID",
    "7f6e41e9-10c0-422c-8776-088fff2a9f48",
)
EMBEDDING_MODEL_KEY = os.getenv(
    "VANE_EMBEDDING_MODEL_KEY",
    "Xenova/all-MiniLM-L6-v2",
)

# ── MCP Server ───────────────────────────────────────────
mcp = FastMCP(
    name="Vane AI Search",
    instructions="Vane — AI search engine with web search, deep research, and cited answers. Powered by DeepSeek V4 Pro.",
    dependencies=["httpx>=0.28.0"],
)


def get_client() -> VaneClient:
    """Создать Vane клиент с настройками из окружения."""
    return VaneClient(
        base_url=VANE_BASE_URL,
        chat_provider_id=CHAT_PROVIDER_ID,
        chat_model_key=CHAT_MODEL_KEY,
        embedding_provider_id=EMBEDDING_PROVIDER_ID,
        embedding_model_key=EMBEDDING_MODEL_KEY,
    )


def _format_sources(sources: list[dict]) -> str:
    """Форматировать источники для вывода."""
    if not sources:
        return ""
    lines = ["\n---", "**Источники:**"]
    for i, s in enumerate(sources[:10], 1):
        title = s.get("metadata", {}).get("title", s.get("title", "Без названия"))
        url = s.get("metadata", {}).get("url", s.get("url", ""))
        if url:
            lines.append(f"{i}. [{title}]({url})")
        else:
            lines.append(f"{i}. {title}")
    return "\n".join(lines)


# ── Tools ────────────────────────────────────────────────


@mcp.tool(
    name="web_search",
    annotations={
        "title": "Веб-поиск через Vane",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def web_search(
    query: str,
    ctx: Context = None,
) -> str:
    """Быстрый веб-поиск с AI-ответом (speed mode).

    Используй для быстрых фактов, текущих событий, цен, новостей.
    Возвращает ответ AI со ссылками на источники.

    Args:
        query: Поисковый запрос на естественном языке.
    """
    client = get_client()

    if ctx:
        await ctx.info(f"🔍 Поиск: {query[:100]}...")
        await ctx.report_progress(0.1, 1.0)

    result = await client.search(query=query, mode="speed", sources=["web"])

    if ctx:
        await ctx.report_progress(1.0, 1.0)

    output = result.message + _format_sources(result.sources)
    logger.info(f"web_search: '{query[:60]}' → {len(result.message)} chars, {len(result.sources)} sources")
    return output


@mcp.tool(
    name="deep_research",
    annotations={
        "title": "Глубокое исследование через Vane",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def deep_research(
    query: str,
    ctx: Context = None,
) -> str:
    """Глубокое исследование с множеством источников (quality mode).

    Используй для сложных вопросов, требующих всестороннего анализа.
    Просматривает множество источников, даёт развёрнутый ответ.

    Args:
        query: Исследовательский запрос на естественном языке.
    """
    client = get_client()

    if ctx:
        await ctx.info(f"🔬 Глубокое исследование: {query[:100]}...")
        await ctx.report_progress(0.05, 1.0)

    result = await client.search(
        query=query,
        mode="quality",
        sources=["web", "academic"],
    )

    if ctx:
        await ctx.report_progress(1.0, 1.0)

    output = result.message + _format_sources(result.sources)
    logger.info(f"deep_research: '{query[:60]}' → {len(result.message)} chars, {len(result.sources)} sources")
    return output


@mcp.tool(
    name="balanced_search",
    annotations={
        "title": "Сбалансированный поиск через Vane",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def balanced_search(
    query: str,
    ctx: Context = None,
) -> str:
    """Сбалансированный поиск — золотая середина (balanced mode).

    Для большинства поисковых запросов. Баланс скорости и глубины.
    Несколько источников, развёрнутый ответ.

    Args:
        query: Поисковый запрос на естественном языке.
    """
    client = get_client()

    if ctx:
        await ctx.info(f"⚖️ Сбалансированный поиск: {query[:100]}...")
        await ctx.report_progress(0.1, 1.0)

    result = await client.search(query=query, mode="balanced", sources=["web"])

    if ctx:
        await ctx.report_progress(1.0, 1.0)

    output = result.message + _format_sources(result.sources)
    logger.info(f"balanced_search: '{query[:60]}' → {len(result.message)} chars, {len(result.sources)} sources")
    return output


@mcp.tool(
    name="search_news",
    annotations={
        "title": "Поиск новостей через Vane",
        "readOnlyHint": True,
        "destructiveHint": False,
    },
)
async def search_news(
    query: str,
    ctx: Context = None,
) -> str:
    """Поиск новостей и обсуждений.

    Используй для поиска свежих новостей, трендов, обсуждений в соцсетях.
    Использует источники web + social.

    Args:
        query: Поисковый запрос (тема новости).
    """
    client = get_client()

    if ctx:
        await ctx.info(f"📰 Поиск новостей: {query[:100]}...")

    result = await client.search(
        query=query,
        mode="speed",
        sources=["web", "social"],
    )

    output = result.message + _format_sources(result.sources)
    logger.info(f"search_news: '{query[:60]}' → {len(result.message)} chars")
    return output


# ── Resources ────────────────────────────────────────────


@mcp.resource("vane://status")
async def vane_status() -> str:
    """Статус Vane сервера и подключённых сервисов."""
    client = get_client()
    try:
        health = await client.health()
        return json.dumps(
            {
                "vane_url": VANE_BASE_URL,
                "vane_status": "ok" if health["ok"] else "error",
                "chat_model": f"{CHAT_PROVIDER_ID}/{CHAT_MODEL_KEY}",
                "embedding_model": f"{EMBEDDING_PROVIDER_ID}/{EMBEDDING_MODEL_KEY}",
                "mcp_version": __version__,
            },
            indent=2,
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps(
            {
                "vane_url": VANE_BASE_URL,
                "vane_status": f"error: {e}",
                "chat_model": CHAT_MODEL_KEY,
                "mcp_version": __version__,
            },
            indent=2,
            ensure_ascii=False,
        )


# ── Main ─────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Vane MCP Server — AI Search Engine через Model Context Protocol",
    )
    parser.add_argument(
        "--sse",
        action="store_true",
        help="Запустить в SSE режиме (для удалённых клиентов)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8053,
        help="Порт для SSE режима (по умолчанию: 8053)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Хост для SSE режима (по умолчанию: 0.0.0.0)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"vane-mcp {__version__}",
    )
    args = parser.parse_args()

    logger.info(f"Vane MCP Server v{__version__}")
    logger.info(f"Vane URL: {VANE_BASE_URL}")
    logger.info(f"Chat Model: {CHAT_PROVIDER_ID}/{CHAT_MODEL_KEY}")
    logger.info(f"Embedding Model: {EMBEDDING_PROVIDER_ID}/{EMBEDDING_MODEL_KEY}")

    if args.sse:
        logger.info(f"Starting SSE server on {args.host}:{args.port}")
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        logger.info("Starting stdio server")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
