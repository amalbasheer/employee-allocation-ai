# app/utils/supabase_client.py
from supabase import create_client, Client
from app.config import settings

supabase_client: Client | None = None

if settings.SUPABASE_URL and settings.SUPABASE_KEY:
    try:
        supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    except Exception as e:
        print(f"⚠️ Failed to initialize Supabase client: {e}")
else:
    print("⚠️ Warning: SUPABASE_URL or SUPABASE_KEY is missing in .env")

def upload_file_to_supabase(file, bucket_name: str, destination_path: str):
    if not supabase_client:
        raise ValueError("Supabase client is not configured. Please set SUPABASE_URL and SUPABASE_KEY in .env.")
    
    # Existing file upload logic here...
    response = supabase_client.storage.from_(bucket_name).upload(destination_path, file)
    return response