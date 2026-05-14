"""
Vane API Client — асинхронный клиент для Vane Search API.

Vane (https://github.com/ItzCrazyKns/Vane) — AI-powered answering engine.
Этот клиент предоставляет Python-интерфейс для поискового API Vane.
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
        chat_provider_id: str = "deepseek",
        chat_model_key: str = "deepseek-v4-pro",
        embedding_provider_id: str = "7f6e41e9-10c0-422c-8776-088fff2a9f48",
        embedding_model_key: str = "Xenova/all-MiniLM-L6-v2",
        timeout: float = 90.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.chat_provider_id = chat_provider_id
        self.chat_model_key = chat_model_key
        self.embedding_provider_id = embedding_provider_id
        self.embedding_model_key = embedding_model_key
        self.timeout = timeout

    async def search(
        self,
        query: str,
        mode: str = "speed",
        sources: Optional[list[str]] = None,
        history: Optional[list[tuple[str, str]]] = None,
    ) -> SearchResult:
        """Выполнить поисковый запрос через Vane.

        Args:
            query: Поисковый запрос.
            mode: Режим поиска — 'speed', 'balanced', 'quality'.
            sources: Источники — ['web'], ['academic'], ['social'], ['web','academic'].
            history: История диалога в формате [("human","msg"),("assistant","msg"),...].

        Returns:
            SearchResult с ответом и источниками.
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

        async with httpx.AsyncClient(timeout=self.timeout, proxy=None) as client:
            resp = await client.post(
                f"{self.base_url}/api/search",
                json=body,
                headers={"Content-Type": "application/json"},
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
        """Проверить здоровье Vane API."""
        async with httpx.AsyncClient(timeout=10.0, proxy=None) as client:
            resp = await client.get(f"{self.base_url}/api/search")
        return {
            "status": resp.status_code,
            "ok": resp.status_code < 500,
        }
