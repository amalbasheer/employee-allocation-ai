import uuid
from supabase import create_client, Client
from app.config import settings

supabase_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def upload_resume_to_supabase(file_bytes: bytes, original_filename: str) -> str:
    """Uploads PDF to 'resumes' bucket and returns public URL."""
    file_path = f"{uuid.uuid4()}_{original_filename}"
    
    supabase_client.storage.from_("resumes").upload(
        path=file_path,
        file=file_bytes,
        file_options={"content-type": "application/pdf"}
    )
    
    return supabase_client.storage.from_("resumes").get_public_url(file_path)