from supabase import create_client, Client
from app.config import settings

if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

# 1. Sanitize URL (trailing slashes cause client requests to hang indefinitely)
supabase_url = settings.SUPABASE_URL.rstrip("/")

# 2. Use Service Role Key if available so backend DB queries bypass RLS locks
supabase_key = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None) or settings.SUPABASE_KEY

supabase: Client = create_client(supabase_url, supabase_key)