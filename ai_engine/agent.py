"""
agent.py
Read-only chat assistant. Answers natural language questions like
"who's available next week" or "suggest trainers for a Data Analytics
program" by giving Gemini a set of tools (functions) it can call to
look up real data — it never writes/assigns anything, matching the
scope sir confirmed.
"""

from google.genai import types
from config import client, LLM_MODEL
from db import get_available_mentors, get_available_interns, get_project, get_project_requirements

SYSTEM_INSTRUCTION = """You are a read-only assistant for RP2's workforce allocation system.
You answer questions about mentor/intern availability and project details using the
tools provided. You NEVER assign, confirm, or modify any allocation — if someone asks
you to assign a person to a project, tell them you can only provide information, and
an admin needs to make the actual assignment in the dashboard."""


def chat_query(user_message: str) -> str:
    """
    Answers one natural-language question using Gemini function calling —
    Gemini decides which of the read-only tools (if any) it needs to call
    to answer, calls them, then writes a plain-language response.

    Args:
        user_message: what the admin typed, e.g. "who's free this week?"

    Returns:
        The assistant's text response.
    """
    tools = [get_available_mentors, get_available_interns, get_project, get_project_requirements]

    response = client.models.generate_content(
        model=LLM_MODEL,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=tools,  # passing the actual Python functions — SDK handles calling them
        ),
    )

    return response.text


if __name__ == "__main__":
    # Quick manual test — run `python agent.py` once DATABASE_URL is set
    answer = chat_query("Which mentors are currently available?")
    print(answer)