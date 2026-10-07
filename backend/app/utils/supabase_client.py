"""
Supabase client abstraction.

All Supabase interactions (database + storage) go through this module.
Never import supabase-py directly outside this file.
"""
import logging
from functools import lru_cache
from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Return a cached Supabase client initialised with the service-role key.

    The service-role key bypasses Row Level Security, which is correct for a
    trusted server-side backend.  It must never be exposed to the frontend.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in the environment. "
            "Copy backend/.env.example to backend/.env and fill in the values."
        )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
