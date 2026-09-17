#services/notifications.py
from dotenv import load_dotenv
load_dotenv()

import resend
import os

resend.api_key = os.getenv("RESEND_API_KEY")


resend.api_key = os.getenv("RESEND_API_KEY")

def send_assignment_notification(
    recipient_email: str, 
    recipient_name: str, 
    project_title: str, 
    description: str,
    start_date: str,
    end_date: str,
    priority: str,
    assigned_intern_name: str = None
):
    intern_line = f"<p>Assigned Intern: <strong>{assigned_intern_name}</strong></p>" if assigned_intern_name else ""

    resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": recipient_email,
        "subject": f"You've been assigned to {project_title}",
        "html": f"""
            <p>Hi {recipient_name},</p>
            <p>You've been assigned to <strong>{project_title}</strong>.</p>
            <p>{description}</p>
            <p>Duration: {start_date} to {end_date}</p>
            <p>Priority: {priority}</p>
            {intern_line}
            <p>Log in to AllignIQ to view full details.</p>
        """
    })

