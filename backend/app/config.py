import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "VoxLead AI"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    MOCK_MODE: bool = os.getenv("MOCK_MODE", "true").lower() in ("true", "1", "yes")

    # Security & Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "voxlead-development-super-secret-key-32-chars-long")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"
    DEFAULT_TENANT_ID: str = os.getenv("DEFAULT_TENANT_ID", "tenant-voxlead-demo")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/voxlead")

    # AI & Providers
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_DIM: int = 1536

    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel

    # LiveKit
    LIVEKIT_URL: str = os.getenv("LIVEKIT_URL", "http://localhost:7880")
    LIVEKIT_API_KEY: str = os.getenv("LIVEKIT_API_KEY", "devkey")
    LIVEKIT_API_SECRET: str = os.getenv("LIVEKIT_API_SECRET", "secret-key-32-chars-long-for-livekit-auth")

    # Business Integrations
    GOOGLE_CALENDAR_CLIENT_ID: str = os.getenv("GOOGLE_CALENDAR_CLIENT_ID", "")
    GOOGLE_CALENDAR_CLIENT_SECRET: str = os.getenv("GOOGLE_CALENDAR_CLIENT_SECRET", "")
    GOOGLE_CALENDAR_REFRESH_TOKEN: str = os.getenv("GOOGLE_CALENDAR_REFRESH_TOKEN", "")
    GOOGLE_CALENDAR_CALENDAR_ID: str = os.getenv("GOOGLE_CALENDAR_CALENDAR_ID", "primary")

    HUBSPOT_ACCESS_TOKEN: str = os.getenv("HUBSPOT_ACCESS_TOKEN", "")

    # RAG parameters
    RAG_TOP_K: int = 4
    RAG_SIMILARITY_THRESHOLD: float = 0.20

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "*"]

    model_config = {
        "env_file": ".env",
        "extra": "allow"
    }

settings = Settings()
