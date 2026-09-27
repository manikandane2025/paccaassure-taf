"""Settings from the container environment (set by sandbox/compose.yaml)."""

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    token_secret: str
    token_ttl_seconds: int
    max_delay_ms: int = 30_000


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    env = os.environ  # noqa: TID251 - the sandbox container reads its own env, not PATAF_ config
    return Settings(
        db_host=env.get("NWH_DB_HOST", "postgres"),
        db_port=int(env.get("NWH_DB_PORT", "5432")),
        db_name=env.get("NWH_DB_NAME", "northwind"),
        db_user=env.get("NWH_DB_USER", "northwind_app"),
        db_password=env["NWH_DB_PASSWORD"],
        token_secret=env["NWH_TOKEN_SECRET"],
        token_ttl_seconds=int(env.get("NWH_TOKEN_TTL_SECONDS", "3600")),
    )
