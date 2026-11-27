"""OpenAI ou tout serveur compatible (Ollama, LM Studio, vLLM) : /chat/completions en mode JSON."""
import time

import httpx

from app.ai.base import ProviderError, RateLimited


class OpenAICompatProvider:
    name = "openai"

    def __init__(self, api_key: str, model: str, base_url: str, timeout: float = 120.0):
        self.api_key, self.model, self.base_url, self.timeout = api_key, model, base_url.rstrip("/"), timeout

    def generate_json(self, system: str, prompt: str) -> str:
        body = {"model": self.model, "temperature": 0.2, "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        last = ""
        for attempt in range(3):
            try:
                r = httpx.post(f"{self.base_url}/chat/completions", json=body, headers=headers, timeout=self.timeout)
            except httpx.HTTPError as e:
                last = type(e).__name__
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 429:
                raise RateLimited("Quota atteint (HTTP 429)")
            if r.status_code >= 500:
                last = f"HTTP {r.status_code}"
                time.sleep(2 ** attempt)
                continue
            if r.status_code != 200:
                raise ProviderError(f"Fournisseur IA HTTP {r.status_code}")
            try:
                return r.json()["choices"][0]["message"]["content"]
            except (KeyError, IndexError, ValueError):
                raise ProviderError("Réponse du fournisseur IA inattendue")
        raise ProviderError(f"Fournisseur IA injoignable ({last})")
