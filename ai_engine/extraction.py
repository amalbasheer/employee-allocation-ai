"""
extraction.py
Turns raw text (a resume, or a project description) into a
structured list of skills using Gemini.

Two source types are supported because the prompt differs slightly:
  - "resume"               -> extracting a person's skills
  - "project_description"  -> extracting a project's required skills
"""

import json
from config import client, LLM_MODEL

EXTRACTION_PROMPT = """You are a skill-extraction engine for a workforce allocation system.
Read the text below and extract every technical skill, tool, domain area, or
certification mentioned. Return ONLY valid JSON, no markdown fences, no preamble.

Format exactly like this:
{{
  "skills": [
    {{"name": "Python", "category": "tech_stack", "confidence": "high"}},
    {{"name": "Data Analytics", "category": "domain", "confidence": "medium"}}
  ]
}}

Rules:
- "category" must be one of: tech_stack, domain, soft_skill
- "confidence" must be one of: high, medium, low
  - high: explicitly named skill (e.g. "Python", "React.js")
  - medium: implied by context (e.g. "built REST APIs" implies backend dev)
  - low: vague or uncertain mention
- Do not invent skills that aren't supported by the text.
- Source type: {source_type}

Text to analyze:
---
{text}
---
"""


def extract_skills_from_text(text: str, source_type: str = "resume") -> dict:
    """
    Calls Gemini to extract structured skills from raw text.

    Args:
        text: the resume text or project description text
        source_type: "resume" or "project_description" (affects nothing
                      in the prompt logic yet, but kept for future tuning
                      and for logging/debugging which pipeline was used)

    Returns:
        dict like {"skills": [{"name": ..., "category": ..., "confidence": ...}, ...]}
        Returns {"skills": [], "error": "..."} if parsing fails, so callers
        can flag it for human review instead of crashing.
    """
    prompt = EXTRACTION_PROMPT.format(source_type=source_type, text=text)

    response = client.models.generate_content(
        model=LLM_MODEL,
        contents=prompt,
    )

    raw_output = response.text.strip()

    # Gemini sometimes wraps JSON in ```json fences even when told not to — strip them
    if raw_output.startswith("```"):
        raw_output = raw_output.strip("`")
        if raw_output.startswith("json"):
            raw_output = raw_output[4:]
        raw_output = raw_output.strip()

    try:
        parsed = json.loads(raw_output)
        if "skills" not in parsed:
            raise ValueError("Response JSON missing 'skills' key")
        return parsed
    except (json.JSONDecodeError, ValueError) as e:
        # Don't crash the pipeline — flag it so a human can review the raw text
        return {"skills": [], "error": str(e), "raw_output": raw_output}


if __name__ == "__main__":
    # Quick manual test — run `python extraction.py` to sanity check the prompt
    sample_resume = """
    Amal Basheer — B.Tech Computer Science, XYZ College.
    Built a full-stack web app using React and FastAPI.
    Completed a machine learning internship working with PyTorch and
    scikit-learn on image classification. Comfortable with SQL and Git.
    """
    result = extract_skills_from_text(sample_resume, source_type="resume")
    print(json.dumps(result, indent=2))