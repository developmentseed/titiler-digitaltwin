"""Titiler-digitaltwin API settings."""

import pydantic


class ApiSettings(pydantic.BaseSettings):
    """FASTAPI application settings."""

    name: str = "titiler"
    cors_origins: str = "*"
    cachecontrol: str = "public, max-age=3600"
    debug: bool = False

    @pydantic.validator("cors_origins")
    def parse_cors_origin(cls, v):
        """Parse CORS origins."""
        return [origin.strip() for origin in v.split(",")]
