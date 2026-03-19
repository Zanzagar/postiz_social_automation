"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """FastAPI backend configuration via pydantic-settings.

    All values are read from environment variables (case-insensitive).
    """

    # Auth
    jwt_secret: str
    api_password: str
    jwt_expiry_minutes: int = 60

    # Postiz
    postiz_api_key: str
    postiz_base_url: str = "https://postiz.sethpc.xyz/api/public/v1"

    # Google Sheets
    spreadsheet_id: str
    google_sheets_credentials: str = "credentials.json"

    # Database
    database_path: str = "data/gvsa.db"

    # Demo
    demo_mode: bool = False

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}
