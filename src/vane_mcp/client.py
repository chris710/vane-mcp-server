"""
Vane API Client — async HTTP client for Vane Search API.

Vane (https://github.com/ItzCrazyKns/Vane) — AI-powered answering engine.
This client provides a Python interface for the Vane search API.
"""

import json
from typing import Optional, Any
from dataclasses import dataclass, field

import httpx


@dataclass
class SearchResult:
    message: str = ""
    sources: list[dict] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


class VaneClient:
    """Async HTTP client for Vane search API."""

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        chat_provider_id: str = "openai",
        chat_model_key: str = "gpt-4o",
        embedding_provider_id: str = "openai",
        embedding_model_key: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
        timeout: float = 3600.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.chat_provider_id = chat_provider_id
        self.chat_model_key = chat_model_key
        self.embedding_provider_id = embedding_provider_id
        self.embedding_model_key = embedding_model_key
        self.api_key = api_key
        self.timeout = timeout

    async def search(
        self,
        query: str,
        mode: str = "speed",
        sources: Optional[list[str]] = None,
        history: Optional[list[tuple[str, str]]] = None,
    ) -> SearchResult:
        """Execute a search query through Vane.

        Args:
            query: Search query.
            mode: Search mode — 'speed', 'balanced', 'quality'.
            sources: Sources — ['web'], ['academic'], ['social'], ['web','academic'].
            history: Dialog history in format [("human","msg"),("assistant","msg"),...].

        Returns:
            SearchResult with answer and sources.
        """
        if sources is None:
            sources = ["web"]
        if history is None:
            history = []

        body = {
            "query": query,
            "optimizationMode": mode,
            "sources": sources,
            "chatModel": {
                "providerId": self.chat_provider_id,
                "key": self.chat_model_key,
            },
            "embeddingModel": {
                "providerId": self.embedding_provider_id,
                "key": self.embedding_model_key,
            },
            "history": history,
        }

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Quality mode (deep research) can take several minutes
        timeout = self.timeout
        if mode == "quality":
            timeout = max(timeout, 3600.0)  # 60 minutes for deep research

        async with httpx.AsyncClient(timeout=timeout, proxy=None) as client:
            resp = await client.post(
                f"{self.base_url}/api/search",
                json=body,
                headers=headers,
            )

        if resp.status_code != 200:
            try:
                err = resp.json()
            except Exception:
                err = {"message": resp.text}
            return SearchResult(
                message=f"Vane API error {resp.status_code}: {err.get('message', 'Unknown')}",
                raw=err,
            )

        data = resp.json()
        return SearchResult(
            message=data.get("message", ""),
            sources=data.get("sources", []),
            raw=data,
        )

    async def health(self) -> dict[str, Any]:
        """Check Vane API health."""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=10.0, proxy=None) as client:
            resp = await client.get(
                f"{self.base_url}/api/search",
                headers=headers,
            )
        return {
            "status": resp.status_code,
            "ok": resp.status_code < 500,
        }
