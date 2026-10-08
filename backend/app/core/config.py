"""Settings from the environment (RELAY_*), read once."""

from functools import lru_cache
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RELAY_", env_file=".env", extra="ignore")

    env: str = "local"
    database_url: str = "postgresql+asyncpg://relay:relay@localhost:5442/relay"
    # In AWS the RDS secret gives the parts separately; when db_host is set they win over database_url.
    db_host: str | None = None
    db_port: int = 5432
    db_name: str = "relay"
    db_user: str = "relay"
    db_password: str | None = None
    redis_url: str = "redis://localhost:6389/0"
    jwt_secret: str = "change-me-local-only-32-characters!"  # noqa: S105 - local default; real secret from Secrets Manager
    app_url: str = "http://localhost:5190"
    cors_origins: list[str] = ["http://localhost:5190"]

    # AWS (LocalStack locally: endpoint set, dummy keys)
    aws_region: str = "us-east-1"
    aws_endpoint_url: str | None = "http://localhost:4566"
    aws_public_endpoint_url: str | None = "http://localhost:4566"  # presigned URLs the browser can reach
    queue_url: str = "http://localhost:4566/000000000000/relay-jobs"
    files_bucket: str = "relay-files"

    # Email: SMTP locally (Mailpit); SES in AWS
    email_backend: str = "smtp"
    smtp_host: str = "localhost"
    smtp_port: int = 1026
    email_from: str = "Relay Support <support@relay.local>"

    @property
    def database_dsn(self) -> str:
        if not self.db_host:
            return self.database_url
        password = quote(self.db_password or "", safe="")
        return f"postgresql+asyncpg://{self.db_user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def is_local(self) -> bool:
        return self.env in {"local", "test"}

    @property
    def cookie_secure(self) -> bool:
        return not self.is_local


@lru_cache
def get_settings() -> Settings:
    return Settings()
