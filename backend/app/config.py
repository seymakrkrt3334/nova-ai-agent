from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    ollama_model: str = Field(default="llama3.2:latest", repr=False)
    ollama_base_url: str = Field(default="http://127.0.0.1:11434", repr=False)
    ollama_embed_model: str = Field(default="nomic-embed-text:latest", repr=False)
    # OLLAMA_HOST is a legacy variable and is intentionally not used.
    ollama_host: str | None = Field(default=None, repr=False)
    database_url: SecretStr | None = Field(default=None, repr=False)
    nova_api_key: SecretStr | None = Field(default=None, repr=False)
    memory_max_distance: float = Field(default=0.55, repr=False)
    memory_duplicate_distance: float = Field(default=0.08, repr=False)
    web_search_provider: str = Field(default="duckduckgo", repr=False)
    web_search_base_url: str | None = Field(default=None, repr=False)
    voice_stt_provider: str = Field(default="disabled", repr=False)
    voice_stt_command: str = Field(default="", repr=False)
    telegram_bot_token: SecretStr | None = Field(default=None, repr=False)
    whatsapp_token: SecretStr | None = Field(default=None, repr=False)
    whatsapp_phone_number_id: str = Field(default="", repr=False)
    instagram_token: SecretStr | None = Field(default=None, repr=False)
    instagram_page_id: str = Field(default="", repr=False)

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        extra="ignore",
        hide_input_in_errors=True,
    )

    def __repr__(self) -> str:
        return "Settings(redacted)"

    def __str__(self) -> str:
        return "Settings(redacted)"


settings = Settings()
