from supabase import create_client, Client
from app.config import settings

if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

# 1. Sanitize URL (prevent hanging requests due to trailing slashes)
supabase_url = settings.SUPABASE_URL.rstrip("/")

# 2. Standard Client (Uses Anon / Public Key)
supabase: Client = create_client(supabase_url, settings.SUPABASE_KEY)

# 3. Admin Client (Explicitly requires Service Role Key for administrative tasks)
service_role_key = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)

if service_role_key:
    supabase_admin: Client = create_client(supabase_url, service_role_key)
else:
    # If service role key is missing, raise warning or mirror client
    print("⚠️ SUPABASE_SERVICE_ROLE_KEY not set. Admin Auth API functions may fail.")
    supabase_admin = supabase