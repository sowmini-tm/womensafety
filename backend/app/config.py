import json
from pathlib import Path
from typing import Annotated, Any, List

from dotenv import load_dotenv
from pydantic import AnyUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

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
    RATE_LIMIT_AUTH_MAX: int = 10
    RATE_LIMIT_OTP_MAX: int = 6
    RATE_LIMIT_SOS_MAX: int = 5
    RATE_LIMIT_SHARED_MAX: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    ENABLE_RATE_LIMITING: bool = False
    MAX_REQUEST_BODY_BYTES: int = 1_000_000
    UPLOAD_DIR: Path = Path("uploads")
    # NoDecode: without it, pydantic-settings JSON-decodes List[str] env values
    # BEFORE the validator below runs, so a plain comma-separated CORS_ORIGINS
    # (the format deployment dashboards use, e.g. Render) crashes the app at
    # import time with SettingsError. With NoDecode the raw string reaches
    # parse_cors_origins, which accepts BOTH CSV and JSON-array formats.
    CORS_ORIGINS: Annotated[List[str], NoDecode] = [
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
            # CORS: wildcard origins are incompatible with credentialed requests
            # and a real risk in production. Require explicit origins.
            origins = self.CORS_ORIGINS or []
            if "*" in [o.strip() for o in origins]:
                raise ValueError(
                    "CORS_ORIGINS must not contain '*' when ENVIRONMENT=production"
                )
            if not origins:
                raise ValueError(
                    "CORS_ORIGINS must be explicitly configured when ENVIRONMENT=production"
                )
            if not self.ENABLE_RATE_LIMITING:
                raise ValueError(
                    "ENABLE_RATE_LIMITING must be True when ENVIRONMENT=production"
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
