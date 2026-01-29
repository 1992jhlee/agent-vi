from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agent_vi"
    database_url_sync: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/agent_vi"

    # DART OpenAPI
    dart_api_key: str = ""

    # Naver Developers
    naver_client_id: str = ""
    naver_client_secret: str = ""

    # YouTube Data API
    youtube_api_key: str = ""

    # LLM Providers
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    default_llm_model: str = "gpt-4o"

    # Frontend
    frontend_url: str = "http://localhost:3000"
    revalidation_secret: str = "change-me"

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000


settings = Settings()
