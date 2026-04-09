"""
Supabase client initialization.
Uses lazy initialization to prevent crash when credentials are placeholders.
"""
from supabase import create_client, Client
from app.config import get_settings
from typing import Optional

_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get or create Supabase client (lazy singleton)."""
    global _client
    if _client is None:
        settings = get_settings()
        try:
            _client = create_client(
                settings.supabase_url,
                settings.supabase_service_role_key
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Supabase client: {e}. "
                "Make sure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set correctly."
            )
    return _client


# Property-like accessor for backward compatibility
class _SupabaseLazy:
    """Lazy proxy that initializes Supabase client on first access."""

    def __getattr__(self, name):
        client = get_supabase_client()
        return getattr(client, name)


supabase = _SupabaseLazy()
