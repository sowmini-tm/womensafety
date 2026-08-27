import json
from pathlib import Path
from typing import List, Any

from dotenv import load_dotenv
from pydantic import AnyUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_parse_json=False,
    )

    DATABASE_URL: AnyUrl
    ENVIRONMENT: str = "development"
    JWT_SECRET_KEY: str = "change_this"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DEV_OTP_MODE: bool = True
    OTP_LENGTH: int = 6
    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RESEND_SECONDS: int = 60
    UPLOAD_DIR: Path = Path("uploads")
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]

    @model_validator(mode="after")
    def enforce_production_jwt_secret(self) -> "Settings":
        """Refuse to run production against the insecure development default."""
        if self.ENVIRONMENT.strip().lower() in {"production", "prod"}:
            candidate = (self.JWT_SECRET_KEY or "").strip()
            if not candidate or candidate == "change_this" or len(candidate) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY must be overridden with a strong value "
                    "(at least 32 characters) when ENVIRONMENT=production"
                )
            # Production must NEVER expose deterministic/dev OTPs.
            if self.DEV_OTP_MODE:
                raise ValueError(
                    "DEV_OTP_MODE must be disabled when ENVIRONMENT=production"
                )
        return self

    @field_validator("CORS_ORIGINS", mode="before")
    def parse_cors_origins(cls, value: Any) -> List[str]:
        if isinstance(value, str):
            raw = value.strip()
            if raw.startswith("[") and raw.endswith("]"):
                trimmed = raw[1:-1].strip()
                if not trimmed:
                    return []
                return [item.strip().strip('"\'') for item in trimmed.split(",") if item.strip()]
            try:
                decoded = json.loads(raw)
                if isinstance(decoded, list):
                    return [str(item) for item in decoded]
            except json.JSONDecodeError:
                pass
            return [item.strip() for item in raw.split(",") if item.strip()]
        return value


settings = Settings()
