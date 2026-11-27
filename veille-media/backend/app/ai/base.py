"""Interface commune des fournisseurs d'IA. Changer de fournisseur = changer AI_PROVIDER dans .env."""
from typing import Protocol


class ProviderError(Exception):
    """Échec ponctuel ou définitif d'un appel (réseau, réponse invalide, contenu bloqué)."""


class RateLimited(ProviderError):
    """Quota atteint (HTTP 429) : on arrête le lot sans compter une tentative perdue."""


class AIProvider(Protocol):
    name: str
    model: str

    def generate_json(self, system: str, prompt: str) -> str:
        """Retourne le texte JSON brut produit par le modèle."""
        ...
