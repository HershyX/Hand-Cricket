from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env."""

    app_name: str = "Hand Cricket Online"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    database_url: str = ""

    # Team size limits. Team A and Team B are configured independently by the
    # host, each within the inclusive range [min_team_size, max_team_size].
    min_team_size: int = 1
    max_team_size: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

MIN_TEAM_SIZE = settings.min_team_size
MAX_TEAM_SIZE = settings.max_team_size
