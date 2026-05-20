from __future__ import annotations

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "komajdon"
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 43200
    email_verification_expire_minutes: int = 10080
    password_reset_expire_minutes: int = 60
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ]
    password_min_length: int = 8
    rate_limit_max: int = 60
    rate_limit_window: int = 60
    rate_limit_auth_max: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def model_post_init(self, __context) -> None:
        if not self.secret_key:
            env_key = os.environ.get("SECRET_KEY", "")
            if env_key:
                self.secret_key = env_key
            else:
                raise ValueError(
                    "SECRET_KEY must be set via environment variable or .env file. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )


settings = Settings()
