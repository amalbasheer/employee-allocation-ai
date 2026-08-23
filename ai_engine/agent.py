"""
agent.py
Read-only chat assistant. Answers natural language questions about
mentor/intern availability, projects, batches, and training engagements
using Gemini function calling — it NEVER assigns/writes anything,
matching the scope sir confirmed.
"""

from google.genai import types
from config import client, LLM_MODEL
from db import (
    get_available_mentors,
    get_available_interns,
    get_project,
    get_project_requirements,
    get_batch,
    get_training_engagement,
    get_next_mentor_for_batch,
)

SYSTEM_INSTRUCTION = """You are a read-only assistant for RP2's workforce allocation system.
You answer questions about mentor/intern availability, projects, student batches, and
training engagements (webinars/workshops/demos) using the tools provided. You NEVER
assign, confirm, propose, or modify any allocation — if someone asks you to assign a
person to anything, tell them you can only provide information, and an admin needs to
make the actual assignment in the dashboard."""


def chat_query(user_message: str) -> str:
    """
    Answers one natural-language question using Gemini function calling —
    Gemini decides which read-only tools it needs, calls them, then
    writes a plain-language response.
    """
    tools = [
        get_available_mentors,
        get_available_interns,
        get_project,
        get_project_requirements,
        get_batch,
        get_training_engagement,
        get_next_mentor_for_batch,
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
    answer = chat_query("Which Data Science mentors are currently available?")
    print(answer)