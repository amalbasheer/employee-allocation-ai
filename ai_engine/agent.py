"""
agent.py
Read-only chat assistant. Answers natural language questions about
mentor/intern availability, project assignments, and skill-based
recommendations using Gemini function calling — NEVER assigns/writes
anything, matching the scope sir confirmed.
"""

from google.genai import types
from .config import client, LLM_MODEL
from .db import (
    engine,
    get_available_mentors,
    get_available_interns,
    get_project,
    get_project_requirements,
    get_batch,
    get_training_engagement,
    get_next_mentor_for_batch,
    search_project_by_title,
    get_intern_details,
    get_employee_details,
    search_training_by_title,
    get_best_mentor_for_domain,
    get_mentor_workload_summary,
    get_project_assignments,
    get_mentor_availability_for_week,
)
from .recommend import recommend_candidates_for_project, recommend_mentor_for_training
from sqlalchemy import text




def get_best_mentor_for_domain(domain: str) -> list[dict]:
    """Ranks available mentors in a domain by their broadest skill strength —
    used for general 'who's the best mentor for X' questions not tied to
    one specific project."""
    mentors = get_available_mentors(domain=domain)
    return sorted(mentors, key=lambda m: m.get("weekly_capacity_hours", 0), reverse=True)[:5]


SYSTEM_INSTRUCTION = """You are a read-only assistant for RP2's workforce allocation system.

ROLE:
- You answer questions about mentor/intern availability (including for specific future weeks),
  who is assigned to projects, batches, and training engagements, and which mentor best fits
  a project or domain based on skills.
- Use the tools provided to look up real data — never guess or make up names.

BOUNDARIES:
- You NEVER assign, confirm, propose, or modify any allocation.
- If someone asks you to assign, propose, or change something, tell them you can only
  provide information, and an admin needs to make the actual assignment in the dashboard.
- For purely informational questions (like "who's available" or "who's assigned to X"),
  just answer directly — do NOT add the read-only disclaimer unless the person is actually
  asking you to take an action.

DOMAIN PARAMETER FORMATTING:
- When calling any tool with a "domain" parameter, always use the full department name
  exactly as stored in the database: "Data Analytics" or "Data Science".
- Never use abbreviations like "DA" or "DS", even if the user asks using the abbreviation.

DOMAIN INFERENCE FOR HYPOTHETICAL TOPICS:
- When asked about a training topic that doesn't exist yet in the system (e.g. "who's
  best for an Agentic AI workshop" when no such engagement exists), use your own
  knowledge to determine which single domain it most likely belongs to before calling
  get_best_mentor_for_domain — do NOT show both domains combined.
- Examples: "Agentic AI," "Machine Learning," "Deep Learning," and "Computer Vision"
  belong to Data Science. "Business Intelligence," "Reporting," and "Dashboards"
  belong to Data Analytics.

OUTPUT FORMATTING:
- Format lists as plain comma-separated text, not markdown bullets or asterisks, since the
  chat display doesn't render markdown formatting.
"""

def chat_query(user_message: str) -> str:
    tools = [
        get_available_mentors,
        get_available_interns,
        get_project,
        get_project_requirements,
        get_batch,
        get_training_engagement,
        get_next_mentor_for_batch,
        get_project_assignments,
        get_mentor_availability_for_week,
        get_best_mentor_for_domain,
        get_mentor_workload_summary,
        recommend_candidates_for_project,
        search_project_by_title,
        get_intern_details,
        get_employee_details,
        search_training_by_title,
        recommend_mentor_for_training,
    ]

    response = client.models.generate_content(
        model=LLM_MODEL,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=tools,
        ),
    )

    return response.text


if __name__ == "__main__":
    for q in [
        "Which mentors are available next week (2026-08-24)?",
        "Who is assigned to project rp2-proj-0004?",
        "Who is the best mentor for a Data Science project?",
    ]:
        print(f"\nQ: {q}")
        print(chat_query(q))

