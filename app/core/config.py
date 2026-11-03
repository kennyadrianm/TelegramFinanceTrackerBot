"""Application configuration and environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env file
load_dotenv(BASE_DIR / ".env")


class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'finance_tracker.db'}"
    )
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # Paths
    DATA_DIR: Path = BASE_DIR / "data"
    EXPORTS_DIR: Path = DATA_DIR / "exports"

    def ensure_directories(self) -> None:
        """Create necessary project directories if they do not exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()

