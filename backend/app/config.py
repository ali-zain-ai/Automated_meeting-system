"""
Application configuration loaded from environment variables.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import pytz


class Settings(BaseSettings):
    """All configuration loaded from environment variables."""

    # Supabase
    supabase_url: str = "https://placeholder.supabase.co"
    supabase_service_role_key: str = "placeholder-key"

    # Zoom Server-to-Server OAuth
    zoom_account_id: str = "placeholder"
    zoom_client_id: str = "placeholder"
    zoom_client_secret: str = "placeholder"

    # Email (Gmail SMTP)
    gmail_user: str = "placeholder@gmail.com"
    gmail_app_password: str = "placeholder-pass"

    # Admin
    admin_email: str = "admin@mindfuelbyali.com"
    admin_password: str = "changeme"
    secret_key: str = "super-secret-key-change-in-production"

    # CORS
    frontend_url: str = "http://localhost:3000"

    # App Settings
    app_name: str = "MindFuelByAli"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Cache and return settings singleton."""
    return Settings()


# Timezone constants
TZ_UTC = pytz.utc
TZ_PKT = pytz.timezone("Asia/Karachi")

# Booking duration constants (in minutes)
CONSULTATION_DURATION = 10
PROJECT_DISCUSSION_DURATION = 30
SLOT_DURATION = 10  # Base slot size
