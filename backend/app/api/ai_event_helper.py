import io
import json
import os
import re
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fpdf import FPDF
from google import genai
from google.genai import types

router = APIRouter()

# Initialize Gemini Client (automatically picks up GEMINI_API_KEY from environment)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# -------------------------------------------------------------------------
# Pydantic Schemas
# -------------------------------------------------------------------------
class WebinarPromptRequest(BaseModel):
    domain: str                                    # e.g., "AI & Machine Learning", "Cloud Security"
    format_type: Optional[str] = "workshop"        # webinar, workshop, demo, seminar
    target_audience: Optional[str] = "Engineers"  # Students, Mid-Level Developers, Executives
    duration_hours: Optional[int] = 2              # Estimated length in hours
    description: Optional[str] = ""               # Additional preferences or custom notes

class SelectedWebinarProposalRequest(BaseModel):
    title: str
    summary: str
    format_type: str
    target_audience: str
    duration_hours: int


# -------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------
def clean_text_for_latin1(text: str) -> str:
    """Replaces non-Latin1 characters commonly output by LLMs with standard ASCII equivalents."""
    replacements = {
        "“": '"', "”": '"', "‘": "'", "’": "'",
        "—": "-", "–": "-", "•": "-", "…": "...",
        "\u200b": "", "\xa0": " "
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text.encode("latin-1", errors="replace").decode("latin-1")


# -------------------------------------------------------------------------
# 1. GENERATE WEBINAR / WORKSHOP SUGGESTIONS (JSON Output)
# -------------------------------------------------------------------------
@router.post("/suggest")
def suggest_webinars(req: WebinarPromptRequest):
    prompt = f"""
    Suggest 3 unique, engaging training session ideas based on these constraints:
    - Domain/Topic: {req.domain}
    - Format Type: {req.format_type}
    - Target Audience: {req.target_audience}
    - Duration: {req.duration_hours} hours
    - User Preferences: {req.description}

    Return a JSON array of objects. Each object must contain:
    - "id": number (1 to 3)
    - "title": engagement title string
    - "summary": 2-sentence overview
    - "format_type": string
    - "duration_hours": number
    - "target_audience": target audience string
    - "key_takeaways": array of 3 strings detailing key learning outcomes
    """

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7,
            ),
        )
        
        webinars = json.loads(response.text)
        return {"webinars": webinars}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Gemini API Error: {str(e)}"
        )


# -------------------------------------------------------------------------
# 2. GENERATE WEBINAR / WORKSHOP PROPOSAL PDF
# -------------------------------------------------------------------------
@router.post("/generate-proposal-pdf")
def generate_webinar_proposal_pdf(req: SelectedWebinarProposalRequest):
    prompt = f"""
    Write a detailed, highly professional Webinar/Workshop Proposal & Syllabus document for:
    - Title: {req.title}
    - Format: {req.format_type}
    - Target Audience: {req.target_audience}
    - Duration: {req.duration_hours} Hours
    - Summary: {req.summary}

    Format the response clearly into these exact sections:
    1. Executive Overview & Learning Objectives
    2. Target Audience & Prerequisites
    3. Detailed Agenda & Module Timeline
    4. Hands-on Exercises & Interactive Components
    5. Speaker & Technical Setup Requirements

    Do not use Markdown formatting like asterisks or hashtags. Use plain text header titles.
    """

    try:
        # 1. Call Gemini
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
            ),
        )
        proposal_text = response.text or ""

        # 2. Setup FPDF Document
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_margins(left=15, top=15, right=15)
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        epw = pdf.epw  # Effective page width

        # Title
        pdf.set_font("Helvetica", style="B", size=16)
        cleaned_title = clean_text_for_latin1(req.title)
        pdf.cell(epw, 10, f"Training Syllabus: {cleaned_title}", new_x="LMARGIN", new_y="NEXT", align="C")

        # Subtitle
        pdf.set_font("Helvetica", style="I", size=10)
        cleaned_sub = clean_text_for_latin1(
            f"Format: {req.format_type.upper()} | Duration: {req.duration_hours} Hours | Audience: {req.target_audience}"
        )
        pdf.cell(epw, 6, cleaned_sub, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(8)

        # 3. Render Body Text
        sanitized_text = clean_text_for_latin1(proposal_text)
        
        for line in sanitized_text.split("\n"):
            line_str = line.strip()
            pdf.set_x(pdf.l_margin)

            if not line_str:
                pdf.ln(4)
                continue
                
            # Render section headers with bold styling
            if re.match(r"^\d+\.\s+", line_str):
                pdf.set_font("Helvetica", style="B", size=12)
                pdf.ln(3)
                pdf.multi_cell(w=epw, h=7, text=line_str, new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", size=10)
            else:
                pdf.multi_cell(w=epw, h=6, text=line_str, new_x="LMARGIN", new_y="NEXT")

        # 4. Stream response buffer
        pdf_bytes = pdf.output()
        pdf_buffer = io.BytesIO(pdf_bytes)
        pdf_buffer.seek(0)

        safe_filename = re.sub(r"[^\w\-.]", "_", req.title)
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="Syllabus_{safe_filename}.pdf"'},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Proposal PDF generation failed: {str(e)}",
        )