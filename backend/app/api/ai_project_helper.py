import io
import json
import os
import re
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fpdf import FPDF
from google import genai
from google.genai import types

router = APIRouter()

# Initialize Gemini Client (automatically picks up GEMINI_API_KEY from environment)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Pydantic Schemas
class ProjectPromptRequest(BaseModel):
    category: str
    tech_stack: Optional[str] = "Python, React"
    difficulty: Optional[str] = "Intermediate"
    description: Optional[str] = ""

class SelectedProjectProposalRequest(BaseModel):
    title: str
    summary: str
    category: str
    target_audience: str


# -------------------------------------------------------------------------
# 1. GENERATE PROJECT SUGGESTIONS (JSON Output)
# -------------------------------------------------------------------------
@router.post("/suggest")
def suggest_projects(req: ProjectPromptRequest):
    prompt = f"""
    Suggest 3 unique project ideas based on these constraints:
    - Category: {req.category}
    - Tech Stack: {req.tech_stack}
    - Difficulty: {req.difficulty}
    - User Preferences: {req.description}

    Return a JSON array of objects. Each object must contain:
    - "id": number (1 to 3)
    - "title": project title string
    - "summary": 2-sentence overview
    - "category": string
    - "difficulty": string
    - "target_audience": target user base string
    """

    try:
        # Gemini forced JSON schema configuration
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7,
            ),
        )
        
        projects = json.loads(response.text)
        return {"projects": projects}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Gemini API Error: {str(e)}"
        )


# -------------------------------------------------------------------------
# 2. GENERATE PROJECT PROPOSAL PDF
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


@router.post("/generate-proposal-pdf")
def generate_proposal_pdf(req: SelectedProjectProposalRequest):
    prompt = f"""
    Write a detailed, highly professional Project Proposal document for:
    - Title: {req.title}
    - Category: {req.category}
    - Summary: {req.summary}
    - Target Audience: {req.target_audience}

    Format the response clearly into these sections:
    1. Executive Summary
    2. Core Features & Capabilities
    3. Technical Architecture & Tech Stack
    4. Project Timeline & Implementation Phases

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

        # 2. Setup FPDF
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_margins(left=15, top=15, right=15)
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Effective Page Width (Page Width minus left and right margins)
        epw = pdf.epw

        # Document Header Title
        pdf.set_font("Helvetica", style="B", size=16)
        cleaned_title = clean_text_for_latin1(req.title)
        pdf.cell(epw, 10, f"Project Proposal: {cleaned_title}", new_x="LMARGIN", new_y="NEXT", align="C")

        # Document Header Subtitle
        pdf.set_font("Helvetica", style="I", size=10)
        cleaned_sub = clean_text_for_latin1(f"Category: {req.category} | Audience: {req.target_audience}")
        pdf.cell(epw, 6, cleaned_sub, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(8)

        # 3. Render Body Content safely using epw
        sanitized_text = clean_text_for_latin1(proposal_text)
        
        for line in sanitized_text.split("\n"):
            line_str = line.strip()
            
            # Ensure X cursor is reset to the left margin before writing each line
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

        # 4. Stream response
        pdf_bytes = pdf.output()
        pdf_buffer = io.BytesIO(pdf_bytes)
        pdf_buffer.seek(0)

        safe_filename = re.sub(r"[^\w\-.]", "_", req.title)
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="Proposal_{safe_filename}.pdf"'},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Proposal generation failed: {str(e)}",
        )