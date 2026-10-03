from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class Config:
    SECRET_KEY: str
    SQLALCHEMY_DATABASE_URI: str
    SQLALCHEMY_TRACK_MODIFICATIONS: bool

    JWT_SECRET_KEY: str
    JWT_ACCESS_TOKEN_EXPIRES: timedelta
    JWT_REFRESH_TOKEN_EXPIRES: timedelta
    JWT_BLACKLIST_ENABLED: bool

    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # OTP
    OTP_LENGTH: int
    OTP_TTL_SECONDS: int
    OTP_MAX_ATTEMPTS: int
    OTP_PROVIDER: str  # "console" (dev) | "twilio"

    # TOTP (2FA)
    TOTP_ISSUER: str

    ENV: str


def get_config() -> Config:
    env = os.getenv("FLASK_ENV", "development")
    return Config(
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY", "dev-secret"),
        SQLALCHEMY_DATABASE_URI=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://wm:wm@localhost:5433/whitemoon",
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY", "dev-jwt-secret"),
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(
            minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "60"))
        ),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(
            days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", "30"))
        ),
        JWT_BLACKLIST_ENABLED=True,
        REDIS_URL=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        CELERY_BROKER_URL=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
        CELERY_RESULT_BACKEND=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
        OTP_LENGTH=int(os.getenv("OTP_LENGTH", "6")),
        OTP_TTL_SECONDS=int(os.getenv("OTP_TTL_SECONDS", "300")),
        OTP_MAX_ATTEMPTS=int(os.getenv("OTP_MAX_ATTEMPTS", "5")),
        OTP_PROVIDER=os.getenv("OTP_PROVIDER", "console"),
        TOTP_ISSUER=os.getenv("TOTP_ISSUER", "White Moon"),
        ENV=env,
    )
