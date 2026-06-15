from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AskDocs API"
    app_origins: str = "http://localhost:3000"
    app_data_dir: Path = Path(__file__).resolve().parents[1] / "data"
    app_sample_dir: Path = Path(__file__).resolve().parents[2] / "samples"
    app_signing_secret: str = "development-only-change-me"
    seed_samples: bool = True
    max_upload_mb: int = 20
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    app_internal_token: str = "development-internal-token"
    chat_requests_per_minute: int = 30
    upload_requests_per_minute: int = 10
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    @property
    def upload_dir(self) -> Path:
        return self.app_data_dir / "uploads"

    @property
    def page_dir(self) -> Path:
        return self.app_data_dir / "pages"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.page_dir.mkdir(parents=True, exist_ok=True)
    return settings
