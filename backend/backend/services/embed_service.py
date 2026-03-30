from __future__ import annotations

import httpx

from backend.config import settings


class EmbedServiceError(Exception):
    pass


class EmbedService:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = "embeddinggemma"
        self.timeout = settings.ollama_timeout_seconds

    async def embed_text(self, text: str) -> list[float]:
        url = f"{self.base_url}/api/embed"
        payload = {
            "model": self.model,
            "input": text,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        embeddings = data.get("embeddings")
        if not embeddings or not isinstance(embeddings, list):
            raise EmbedServiceError("Ollama response does not contain embeddings")

        vector = embeddings[0]
        if not isinstance(vector, list):
            raise EmbedServiceError("Invalid embedding vector format")

        return vector


embed_service = EmbedService()
