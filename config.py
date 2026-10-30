import os
from pathlib import Path
import secrets

from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent

# Load .env file natively if it exists
env_path = BASE_DIR / ".env"
if env_path.is_file():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
DATABASE_DIR = DATA_DIR / "database"

# Ensure directories exist
for d in [DATA_DIR, UPLOAD_DIR, SYNTHETIC_DIR, DATABASE_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class Settings(BaseModel):
    # App Information
    APP_NAME: str = "Hirexp Ai"
    APP_TAGLINE: str = "Resume screening with AI-powered interview using interactive AI avatars."
    VERSION: str = "1.0.0"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{DATABASE_DIR / 'hiresphere.db'}"
    )

    # Security & Tokens
    SECRET_KEY: str = os.getenv("SECRET_KEY") or secrets.token_urlsafe(48)
    INVITATION_TOKEN_EXPIRE_HOURS: int = int(os.getenv("INVITATION_TOKEN_EXPIRE_HOURS", "72"))
    PASSWORD_SETUP_TOKEN_EXPIRE_HOURS: int = int(os.getenv("PASSWORD_SETUP_TOKEN_EXPIRE_HOURS", "48"))
    SESSION_EXPIRE_HOURS: int = int(os.getenv("SESSION_EXPIRE_HOURS", "24"))

    # App Portal Base URLs
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:8501")

    # Email & SMTP Integration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "recruitment@hiresphere.ai")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "HireSphere AI Recruitment Team")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
    SMTP_MOCK_MODE: bool = os.getenv("SMTP_MOCK_MODE", "true").lower() in ("true", "1", "yes")

    # Anthropic Claude API Configuration
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    USE_MOCK_AI: bool = os.getenv(
        "USE_MOCK_AI", "true" if not os.getenv("ANTHROPIC_API_KEY") else "false"
    ).lower() in ("true", "1", "yes")

    # Document Processing & Concurrency
    MAX_UPLOAD_SIZE_MB: int = 25
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "6"))
    BATCH_CHUNK_SIZE: int = 25
    ALLOWED_EXTENSIONS: list[str] = [".pdf", ".docx"]

    # Screening Weights Default
    DEFAULT_WEIGHT_KEYWORDS: float = 0.25
    DEFAULT_WEIGHT_SIMILARITY: float = 0.25
    DEFAULT_WEIGHT_EXPERIENCE: float = 0.25
    DEFAULT_WEIGHT_SEMANTIC: float = 0.25
    SHORTLIST_THRESHOLD: float = 70.0

    # Privacy & Retention
    DATA_RETENTION_DAYS: int = 90
    ALLOW_AUTO_PURGE: bool = True


settings = Settings()
