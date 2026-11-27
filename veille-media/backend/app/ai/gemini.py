"""Google Gemini via l'API REST (generativelanguage.googleapis.com). La clé reste côté serveur."""
import time

import httpx

from app.ai.base import ProviderError, RateLimited

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout: float = 60.0):
        self.api_key, self.model, self.timeout = api_key, model, timeout

    def generate_json(self, system: str, prompt: str) -> str:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
        }
        last = ""
        for attempt in range(3):
            try:
                r = httpx.post(ENDPOINT.format(model=self.model), json=body, timeout=self.timeout,
                               headers={"x-goog-api-key": self.api_key})
            except httpx.HTTPError as e:
                last = type(e).__name__
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 429:
                raise RateLimited("Quota Gemini atteint (HTTP 429)")
            if r.status_code >= 500:
                last = f"HTTP {r.status_code}"
                time.sleep(2 ** attempt)
                continue
            if r.status_code != 200:
                # on ne recopie pas le corps entier : il peut contenir des détails de requête
                msg = ""
                try:
                    msg = r.json().get("error", {}).get("message", "")
                except ValueError:
                    pass
                raise ProviderError(f"Gemini HTTP {r.status_code} : {msg[:300]}")
            data = r.json()
            if data.get("promptFeedback", {}).get("blockReason"):
                raise ProviderError(f"Contenu bloqué par Gemini ({data['promptFeedback']['blockReason']})")
            try:
                parts = data["candidates"][0]["content"]["parts"]
                return "".join(p.get("text", "") for p in parts)
            except (KeyError, IndexError, TypeError):
                raise ProviderError("Réponse Gemini vide ou inattendue")
        raise RateLimited(f"Gemini indisponible ({last}) : nouvel essai plus tard")
