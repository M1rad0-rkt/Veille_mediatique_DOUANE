from functools import lru_cache

from app.ai.base import AIProvider
from app.core.config import settings


@lru_cache
def get_provider() -> AIProvider | None:
    """None = IA non configurée : les articles restent « en attente », rien n'est inventé."""
    if settings.ai_provider == "gemini" and settings.gemini_api_key:
        from app.ai.gemini import GeminiProvider
        return GeminiProvider(settings.gemini_api_key, settings.gemini_model)
    if settings.ai_provider == "openai" and (settings.openai_api_key or "localhost" in settings.openai_base_url
                                             or "host.docker.internal" in settings.openai_base_url):
        from app.ai.openai_compat import OpenAICompatProvider
        return OpenAICompatProvider(settings.openai_api_key, settings.openai_model, settings.openai_base_url)
    return None


def ai_info() -> dict:
    p = get_provider()
    return {"provider": settings.ai_provider, "model": getattr(p, "model", None), "configured": p is not None}
