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
BOUNDARIES:
- NEVER add the disclaimer about being "read-only" or "admin needs to assign" when
  answering a question like "who is available," "who is the best mentor," or "who
  should be assigned" — these are informational questions, not action requests.
- ONLY add that disclaimer if the user explicitly asks you to perform an action,
  like "assign X to Y" or "propose X for this project."

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

DISTINGUISHING COMMITMENT TYPES:
- If asked specifically about "projects," only report project-type commitments in
  your answer — do not mention batch or training commitments.
- If asked specifically about "training," "workshops," or "webinars," only report
  training-type commitments.
- If asked specifically about "batches," only report batch-type commitments.
- Only combine all types together if the question is general and doesn't specify
  a particular type.

LOCATION AND AUDIENCE FOR TRAINING RECOMMENDATIONS:
- If someone asks about a SPECIFIC, EXISTING training engagement (you can look it up
  by name), just call recommend_mentor_for_training and give the answer directly —
  the engagement already has its own region/audience stored, no need to ask.
- ONLY ask "which region, which audience" when the training doesn't exist yet
  (a hypothetical/future topic with no real engagement to look up).

EXPLAINING RECOMMENDATIONS:
- When explaining why someone is recommended, be accurate about tradeoffs — if
  their audience or region doesn't perfectly match the training's requirements,
  say so honestly (e.g. "Aravind is the top skill match, though note his usual
  audience is professionals while this session is for college students").
- Don't imply a perfect match if the underlying score reflects a partial mismatch.

EXPLAINING RECOMMENDATIONS FOR EXISTING TRAININGS:
- For a specific, existing training engagement, you already know its real
  location/region and audience from the data — state them directly and
  confidently, don't hedge with phrases like "if your workshop is elsewhere"
  or "you may want to consider."
- Example of what NOT to say: "his preferred region is Kochi, if your workshop
  is being held in a different city..."
- Example of what TO say: "This workshop is scheduled for [region] with a
  [audience] audience. Aravind's preferred region is Kochi and his usual
  audience is professionals — [state clearly whether this is a match or
  mismatch, and how it affected his ranking]."

CLARIFYING AMBIGUOUS "BEST MENTOR" QUESTIONS:
- If asked "who is the best mentor for [domain/topic]" without specifying whether
  it's for a PROJECT, a TRAINING/workshop, or a STUDENT BATCH, ask which one they
  mean before answering — these use different matching criteria (projects and
  batches don't use region/audience, only training does).

HANDLING DUPLICATE TRAINING NAMES:
- If search_training_by_title returns MORE than one result for the same
  or similar name, do NOT pick one arbitrarily — list all matches with their
  location/institution/date, and ask the user which specific one they mean
  before giving a recommendation.
  
OUTPUT LENGTH:
- Keep every answer to 1-2 short sentences maximum, unless the user explicitly
  asks for detail, a list, or an explanation ("why", "explain", "rank all").
- Never repeat the same fact twice in one answer.
- Do not add extra caveats, suggestions, or "you might want to consider..."
  unless directly relevant and necessary to answer the question asked.
- State facts plainly and directly — avoid hedging language like "may be,"
  "could be," "you might want to," when you already have the real data.

OUTPUT FORMATTING:
- Format lists as plain comma-separated text, not markdown bullets or asterisks, since the
  chat display doesn't render markdown formatting.
"""

def chat_query(user_message: str, conversation_history: list = None) -> str:
    """
    conversation_history: list of {"query": ..., "response": ...} from
    earlier in THIS session, passed in by the caller (frontend keeps this
    in memory, not persisted to a database — session ends, history clears).
    """
    history_text = ""
    for h in (conversation_history or []):
        history_text += f"User: {h['query']}\nAssistant: {h['response']}\n\n"

    full_prompt = f"{history_text}User: {user_message}" if history_text else user_message

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
        contents=full_prompt,
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

