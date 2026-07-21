#!/usr/bin/env python3
"""
Vane MCP Server — Model Context Protocol server for Vane AI Search Engine.

Connects Vane as a set of MCP tools to any MCP client:
- Claude Desktop, Cursor, OpenCode, Continue, Windsurf, etc.

Architecture:
    MCP Client ──(stdio/SSE)──> VaneMCPServer ──(HTTP)──> Vane API (localhost:3000)
                                                                │
                                                           SearxNG (localhost:8080)
                                                                │
                                                           OpenAI-compatible LLM API

All configuration is passed via environment variables from the MCP client config.

Tools:
    web_search      — fast web search (speed mode)
    deep_research   — in-depth research (quality mode)
    balanced_search — balanced search (balanced mode)
    search_news     — news and discussion search (web + social)

Usage:
    uv run vane-mcp                   # stdio mode (for Claude Desktop, OpenCode)
    uv run vane-mcp --sse --port 8053 # SSE mode (for remote clients)

Dependencies:
    mcp>=1.14.0, httpx>=0.28.0
"""

import os
import sys
import json
import logging
import argparse
import traceback
from typing import Optional, Any

import httpx
from mcp.server.fastmcp import FastMCP, Context
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource, ToolAnnotations
from mcp.server import Server

from vane_mcp.client import VaneClient, SearchResult
from vane_mcp import __version__

# ── Logging ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [vane-mcp] %(levelname)s %(message)s",
)
logger = logging.getLogger("vane-mcp")

# ── Config ───────────────────────────────────────────────
# All configuration is read from environment variables.
# These are set in the MCP client's config file (the "env" section).
#
# To find available provider IDs and model keys, run:
#   curl http://localhost:3000/api/providers
#
# Provider IDs are UUIDs (e.g., bb877f6f-a8a4-47e8-8381-fcb3812401a1)
VANE_BASE_URL = os.getenv("VANE_BASE_URL", "http://localhost:3000")
CHAT_PROVIDER_ID = os.getenv("VANE_CHAT_PROVIDER_ID", "")
CHAT_MODEL_KEY = os.getenv("VANE_CHAT_MODEL_KEY", "")
EMBEDDING_PROVIDER_ID = os.getenv("VANE_EMBEDDING_PROVIDER_ID", "")
EMBEDDING_MODEL_KEY = os.getenv("VANE_EMBEDDING_MODEL_KEY", "")
VANE_API_KEY = os.getenv("VANE_API_KEY", "")

# ── MCP Server ───────────────────────────────────────────
mcp = FastMCP(
    name="Vane AI Search",
    instructions="Vane — AI search engine with web search, deep research, and cited answers.",
    dependencies=["httpx>=0.28.0"],
)

# Reusable annotation objects
_READ_ONLY_ANNOTATIONS = ToolAnnotations(
    title="Vane Search Tool",
    readOnlyHint=True,
    destructiveHint=False,
)


def get_client() -> VaneClient:
    """Create a Vane client with settings from environment variables."""
    return VaneClient(
        base_url=VANE_BASE_URL,
        chat_provider_id=CHAT_PROVIDER_ID,
        chat_model_key=CHAT_MODEL_KEY,
        embedding_provider_id=EMBEDDING_PROVIDER_ID,
        embedding_model_key=EMBEDDING_MODEL_KEY,
        api_key=VANE_API_KEY if VANE_API_KEY else None,
    )


def _format_sources(sources: list[dict]) -> str:
    """Format sources for output."""
    if not sources:
        return ""
    lines = ["\n---", "**Sources:**"]
    for i, s in enumerate(sources[:10], 1):
        title = s.get("metadata", {}).get("title", s.get("title", "Untitled"))
        url = s.get("metadata", {}).get("url", s.get("url", ""))
        if url:
            lines.append(f"{i}. [{title}]({url})")
        else:
            lines.append(f"{i}. {title}")
    return "\n".join(lines)


async def _safe_ctx_info(ctx, message: str) -> None:
    """Safely call ctx.info(), ignoring errors if context is unavailable."""
    if ctx is None:
        return
    try:
        await ctx.info(message)
    except Exception:
        pass


async def _safe_ctx_progress(ctx, progress: float, total: float) -> None:
    """Safely call ctx.report_progress(), ignoring errors if context is unavailable."""
    if ctx is None:
        return
    try:
        await ctx.report_progress(progress, total)
    except Exception:
        pass


def _handle_search_result(result: SearchResult, tool_name: str, query: str) -> str:
    """Process search result and handle errors uniformly."""
    if result.message.startswith("Vane API error"):
        logger.error(
            f"{tool_name}: API error for '{query[:60]}': {result.message}"
        )
        return f"Error: {result.message}\n\nRaw response: {json.dumps(result.raw, indent=2, ensure_ascii=False, default=str)[:500]}"

    output = result.message + _format_sources(result.sources)
    logger.info(
        f"{tool_name}: '{query[:60]}' → {len(result.message)} chars, {len(result.sources)} sources"
    )
    return output


# ── Tools ────────────────────────────────────────────────


@mcp.tool(
    name="web_search",
    annotations=_READ_ONLY_ANNOTATIONS,
)
async def web_search(
    query: str,
    ctx: Context = None,
) -> str:
    """Fast web search with AI answer (speed mode).

    Use for quick facts, current events, prices, news.
    Returns AI answer with source links.

    Args:
        query: Natural language search query.
    """
    client = get_client()
    logger.info(f"web_search called with query: {query[:100]}")

    await _safe_ctx_info(ctx, f"🔍 Search: {query[:100]}...")
    await _safe_ctx_progress(ctx, 0.1, 1.0)

    try:
        result = await client.search(query=query, mode="speed", sources=["web"])
    except Exception as e:
        logger.error(f"web_search exception: {e!r}\n{traceback.format_exc()}")
        return f"Search failed: {type(e).__name__}: {e}"

    await _safe_ctx_progress(ctx, 1.0, 1.0)

    return _handle_search_result(result, "web_search", query)


@mcp.tool(
    name="deep_research",
    annotations=_READ_ONLY_ANNOTATIONS,
)
async def deep_research(
    query: str,
    ctx: Context = None,
) -> str:
    """In-depth research with multiple sources (quality mode).

    Use for complex questions requiring comprehensive analysis.
    Examines multiple sources, provides detailed answer.

    Args:
        query: Natural language research query.
    """
    client = get_client()
    logger.info(f"deep_research called with query: {query[:100]}")

    await _safe_ctx_info(ctx, f"🔬 Deep research: {query[:100]}...")
    await _safe_ctx_progress(ctx, 0.05, 1.0)

    try:
        result = await client.search(
            query=query,
            mode="quality",
            sources=["web", "academic"],
        )
    except Exception as e:
        logger.error(f"deep_research exception: {e!r}\n{traceback.format_exc()}")
        return f"Research failed: {type(e).__name__}: {e}"

    await _safe_ctx_progress(ctx, 1.0, 1.0)

    return _handle_search_result(result, "deep_research", query)


@mcp.tool(
    name="balanced_search",
    annotations=_READ_ONLY_ANNOTATIONS,
)
async def balanced_search(
    query: str,
    ctx: Context = None,
) -> str:
    """Balanced search — the sweet spot (balanced mode).

    For most search queries. Balance of speed and depth.
    Multiple sources, detailed answer.

    Args:
        query: Natural language search query.
    """
    client = get_client()
    logger.info(f"balanced_search called with query: {query[:100]}")

    await _safe_ctx_info(ctx, f"⚖️ Balanced search: {query[:100]}...")
    await _safe_ctx_progress(ctx, 0.1, 1.0)

    try:
        result = await client.search(query=query, mode="balanced", sources=["web"])
    except Exception as e:
        logger.error(f"balanced_search exception: {e!r}\n{traceback.format_exc()}")
        return f"Search failed: {type(e).__name__}: {e}"

    await _safe_ctx_progress(ctx, 1.0, 1.0)

    return _handle_search_result(result, "balanced_search", query)


@mcp.tool(
    name="search_news",
    annotations=_READ_ONLY_ANNOTATIONS,
)
async def search_news(
    query: str,
    ctx: Context = None,
) -> str:
    """Search news and discussions.

    Use for finding fresh news, trends, discussions in social media.
    Uses web + social sources.

    Args:
        query: Search query (news topic).
    """
    client = get_client()
    logger.info(f"search_news called with query: {query[:100]}")

    await _safe_ctx_info(ctx, f"📰 News search: {query[:100]}...")

    try:
        result = await client.search(
            query=query,
            mode="speed",
            sources=["web", "social"],
        )
    except Exception as e:
        logger.error(f"search_news exception: {e!r}\n{traceback.format_exc()}")
        return f"News search failed: {type(e).__name__}: {e}"

    return _handle_search_result(result, "search_news", query)


# ── Resources ────────────────────────────────────────────


@mcp.resource("vane://status")
async def vane_status() -> str:
    """Status of Vane server and connected services."""
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
        description="Vane MCP Server — AI Search Engine via Model Context Protocol",
    )
    parser.add_argument(
        "--sse",
        action="store_true",
        help="Run in SSE mode (for remote clients)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8053,
        help="Port for SSE mode (default: 8053)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for SSE mode (default: 0.0.0.0)",
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
