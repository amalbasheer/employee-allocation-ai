import secrets
import resend
from supabase import create_client, Client
from app.config import settings

# Initialize Supabase Admin Client using Service Role Key
supabase_admin: Client | None = None

supabase_url = getattr(settings, "SUPABASE_URL", None)
supabase_service_key = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)

if supabase_url and supabase_service_key:
    try:
        supabase_admin = create_client(supabase_url, supabase_service_key)
    except Exception as e:
        print(f"⚠️ Failed to initialize Supabase Admin client: {e}")
else:
    print("⚠️ Warning: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing in settings")

# Initialize Resend API Key
resend_key = getattr(settings, "RESEND_API_KEY", None)
if resend_key:
    resend.api_key = resend_key
else:
    print("⚠️ Warning: RESEND_API_KEY is missing in settings")

# Load verified domains from settings
raw_domains = getattr(settings, "VERIFIED_DOMAINS", "rp2.com,idatalytics.com")
VERIFIED_DOMAINS = set(d.strip().lower() for d in raw_domains.split(",") if d.strip())


def generate_activation_token() -> str:
    return secrets.token_urlsafe(32)


def resolve_sender_email(admin_email: str) -> str:
    """Dynamically matches admin email domain to verified Resend domains."""
    if admin_email and "@" in admin_email:
        domain = admin_email.split("@")[1].lower().strip()
        if domain in VERIFIED_DOMAINS:
            return f"no-reply@{domain}"

    fallback_sender = getattr(settings, "SENDER_EMAIL", "onboarding@resend.dev")
    return fallback_sender


def send_activation_email(
    to_email: str, 
    employee_name: str, 
    token: str, 
    admin_name: str, 
    admin_email: str
):
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
    activation_link = f"{frontend_url}/activate?token={token}"
    sender_address = resolve_sender_email(admin_email)

    params: resend.Emails.SendParams = {
        "from": f"AlignIQ <{sender_address}>",
        "to": [to_email],
        "subject": "Activate Your AlignIQ Workspace Account",
        "html": f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
            <h2 style="color: #2563eb;">Welcome to AlignIQ, {employee_name}!</h2>
            <p><strong>{admin_name}</strong> ({admin_email}) has invited you to join the workspace.</p>
            <p>Click the button below to complete your account setup and set your password:</p>
            <div style="margin: 28px 0;">
                <a href="{activation_link}" 
                   style="background-color: #2563eb; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                   Activate Account
                </a>
            </div>
            <p style="font-size: 13px; color: #666;">This invitation link will expire in 48 hours.</p>
            <p style="font-size: 13px; color: #666;">If the button does not work, copy and paste this link into your browser:<br>
            <a href="{activation_link}" style="color: #2563eb;">{activation_link}</a></p>
        </div>
        """
    }
    return resend.Emails.send(params)