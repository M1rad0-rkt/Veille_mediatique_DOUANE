from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Veille Média"
    environment: str = "development"
    database_url: str
    secret_key: str
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    cors_origins: str = "http://localhost:5173"
    cookie_secure: bool = False
    rate_limit_enabled: bool = True
    timezone: str = "Indian/Antananarivo"

    first_admin_email: str | None = None
    first_admin_password: str | None = None
    first_admin_name: str = "Administrateur"

    # --- Collecte (Phase 3) ---
    user_agent: str = "VeilleMediaBot/1.0 (veille interne; contact: voir administrateur)"
    http_timeout_seconds: float = 20.0
    http_delay_seconds: float = 1.0           # pause minimale entre deux requêtes vers un même site
    max_articles_per_run: int = 40            # plafond par source et par passage
    fetch_full_content: bool = True           # aller chercher le texte complet des articles
    max_future_days: int = 1                  # une date de publication plus lointaine est jugée incertaine

    # --- IA (Phase 4) ---
    ai_provider: str = "gemini"               # gemini | openai | none
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"   # ou un serveur local compatible (Ollama, LM Studio)
    openai_model: str = "gpt-4o-mini"
    ai_requests_per_minute: int = 8           # reste sous les quotas gratuits ; 0 = pas de limite
    ai_batch_size: int = 10
    ai_max_attempts: int = 3
    ai_min_content_chars: int = 400           # en dessous : pas de résumé (aucun texte inventé)
    ai_max_input_chars: int = 12000

    @field_validator("secret_key")
    @classmethod
    def _secret_long_enough(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY doit contenir au moins 32 caractères")
        return v

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
