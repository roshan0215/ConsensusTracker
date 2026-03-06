from __future__ import annotations

from functools import lru_cache
import secrets
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ConsensusTracker"
    environment: str = Field(default="development", description="development|staging|production")
    secret_key: str | None = Field(default=None, validation_alias="SECRET_KEY", description="Used for session signing, etc.")

    frontend_url: str = Field(default="http://localhost:3000")
    cors_allow_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Comma-separated list of allowed CORS origins",
    )

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/consensustracker",
        validation_alias="DATABASE_URL",
    )

    # DigitalOcean Gradient AI (Management API)
    # Used for knowledge base operations and attaching KBs to agents.
    digitalocean_api_token: str | None = Field(default=None, validation_alias="DIGITALOCEAN_API_TOKEN")
    digitalocean_project_id: str | None = Field(default=None, validation_alias="DIGITALOCEAN_PROJECT_ID")
    gradient_region: str = Field(default="tor1", validation_alias="GRADIENT_REGION")
    gradient_embedding_model: str = Field(default="text-embedding-3-large", validation_alias="GRADIENT_EMBEDDING_MODEL")

    # Gradient agent chat endpoints (Agent Endpoint + Access Key)
    extraction_agent_endpoint: str | None = Field(default=None, validation_alias="EXTRACTION_AGENT_ENDPOINT")
    extraction_agent_access_key: str | None = Field(default=None, validation_alias="EXTRACTION_AGENT_ACCESS_KEY")
    router_agent_endpoint: str | None = Field(default=None, validation_alias="ROUTER_AGENT_ENDPOINT")
    router_agent_access_key: str | None = Field(default=None, validation_alias="ROUTER_AGENT_ACCESS_KEY")

    # Agent UUIDs (for attaching knowledge bases)
    router_agent_uuid: str | None = Field(default=None, validation_alias="ROUTER_AGENT_UUID")
    analysis_agent_uuid: str | None = Field(default=None, validation_alias="ANALYSIS_AGENT_UUID")

    # Google
    google_service_account_json: str | None = Field(default=None, validation_alias="GOOGLE_SERVICE_ACCOUNT_JSON")

    # Google OAuth (for user login + doc access on behalf of users)
    google_oauth_client_id: str | None = Field(default=None, validation_alias="GOOGLE_OAUTH_CLIENT_ID")
    google_oauth_client_secret: str | None = Field(default=None, validation_alias="GOOGLE_OAUTH_CLIENT_SECRET")
    google_oauth_redirect_uri: str = Field(
        default="http://localhost:8000/api/auth/google/callback",
        validation_alias="GOOGLE_OAUTH_REDIRECT_URI",
    )

    # PubMed / NCBI
    ncbi_email: str | None = Field(default=None, validation_alias="NCBI_EMAIL")
    ncbi_api_key: str | None = Field(default=None, validation_alias="NCBI_API_KEY")

    # Email (Gmail SMTP)
    gmail_user: str | None = Field(default=None, validation_alias="GMAIL_USER")
    gmail_app_password: str | None = Field(default=None, validation_alias="GMAIL_APP_PASSWORD")

    # Cron protection for scheduled runs (recommended in production)
    cron_token: str | None = Field(default=None, validation_alias="CRON_TOKEN")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.environment == "development" and not settings.secret_key:
        # Dev convenience: allow auth flows to run without forcing a committed secret.
        # Tokens will be invalid after a restart, which is fine for local dev.
        settings.secret_key = secrets.token_urlsafe(32)
    return settings
