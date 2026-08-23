"""
extraction.py
Turns raw text (a resume, or a project description) into a
structured list of skills using Gemini — output shape differs by
source_type, matching what each destination table actually needs.
"""

import json
from config import client, LLM_MODEL

RESUME_PROMPT = """You are a skill-extraction engine for a workforce allocation system.
Read the resume text below and extract every technical skill, tool, domain area,
or certification mentioned. Return ONLY valid JSON, no markdown fences, no preamble.

Format exactly like this:
{{
  "skills": [
    {{"name": "Python", "category": "tech_stack", "proficiency_level": 4, "confidence": 0.92}},
    {{"name": "Data Analytics", "category": "domain", "proficiency_level": 3, "confidence": 0.65}}
  ]
}}

Rules:
- "category" must be one of: tech_stack, domain, soft_skill
- "proficiency_level" is an integer 1-5, inferred from how the resume describes their
  experience with this skill:
  - 5: expert-level, led projects, years of deep hands-on use
  - 4: strong, regular hands-on experience
  - 3: solid working knowledge, used in real projects
  - 2: basic familiarity, coursework or brief exposure
  - 1: mentioned only, no clear evidence of real use
- "confidence" is a decimal between 0.0 and 1.0, representing how confident YOU are
  that this extraction is accurate (higher = more explicit/clear mention in the text,
  lower = inferred or ambiguous)
- Do not invent skills that aren't supported by the text.

Resume text to analyze:
---
{text}
---
"""

PROJECT_PROMPT = """You are a skill-extraction engine for a workforce allocation system.
Read the project description below and extract every technical skill, tool, domain area,
or certification required to do this work. Return ONLY valid JSON, no markdown fences, no preamble.

Format exactly like this:
{{
  "skills": [
    {{"name": "Python", "category": "tech_stack", "min_proficiency": 4, "is_mandatory": true}},
    {{"name": "Docker", "category": "tech_stack", "min_proficiency": 2, "is_mandatory": false}}
  ]
}}

Rules:
- "category" must be one of: tech_stack, domain, soft_skill
- "min_proficiency" is an integer 1-5, the minimum skill level someone needs to do this work,
  inferred from context:
  - 5: "expert-level", "deep expertise", "advanced mastery" required
  - 4: "strong experience", "proficient" required
  - 3: "solid working knowledge", "comfortable with"
  - 2: "basic familiarity", "some exposure" is enough
  - 1: no strong signal, treat as a minimum baseline
- "is_mandatory" is true if the text implies this is required/must-have, false if it's
  mentioned as a bonus/nice-to-have/preferred
- Do not invent skills that aren't supported by the text.

Project description to analyze:
---
{text}
---
"""


def extract_skills_from_text(text: str, source_type: str = "resume") -> dict:
    """
    Calls Gemini to extract structured skills from raw text.

    Args:
        text: the resume text or project description text
        source_type: "resume" -> returns proficiency_level + confidence
                      (for intern_skills/employee_skills)
                     "project_description" -> returns min_proficiency + is_mandatory
                      (for project_requirements)

    Returns:
        dict like {"skills": [...]} shaped according to source_type.
        Returns {"skills": [], "error": "..."} if parsing fails, so callers
        can flag it for human review instead of crashing.
    """
    if source_type == "resume":
        prompt = RESUME_PROMPT.format(text=text)
    else:
        prompt = PROJECT_PROMPT.format(text=text)

    response = client.models.generate_content(
        model=LLM_MODEL,
        contents=prompt,
    )

    raw_output = response.text.strip()

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
        return {"skills": [], "error": str(e), "raw_output": raw_output}


if __name__ == "__main__":
    sample_resume = """
    Tom John — B.Tech Computer Science, XYZ College.
    Built a full-stack web app using React and FastAPI.
    Completed a machine learning internship working with PyTorch and
    scikit-learn on image classification. Comfortable with SQL and Git.
    """
    print("RESUME extraction:")
    print(json.dumps(extract_skills_from_text(sample_resume, "resume"), indent=2))

    sample_project = """
    We need to build a fraud detection pipeline using Python and machine
    learning. Strong Python skills are required. Experience with PyTorch
    would be a bonus but isn't required.
    """
    print("\nPROJECT DESCRIPTION extraction:")
    print(json.dumps(extract_skills_from_text(sample_project, "project_description"), indent=2))