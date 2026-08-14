"""
config.py
Central place for API keys, model names, and the Gemini client.
Every other module in ai_engine imports from here so there's one
place to change models or keys.
"""

import os
from dotenv import load_dotenv
from google import genai

load_dotenv()  # reads .env in this folder (make sure .env is in .gitignore)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise EnvironmentError(
        "GEMINI_API_KEY not found. Create a .env file in ai_engine/ with:\n"
        "GEMINI_API_KEY=your-key-here"
    )

client = genai.Client(api_key=GEMINI_API_KEY)

# Model names — change here if you switch models later, nowhere else
LLM_MODEL = "gemini-3.1-flash-lite"      # used for skill extraction + chat
EMBEDDING_MODEL = "gemini-embedding-001"  # used for all embeddings
EMBEDDING_DIM = 768                       # must match Vector(768) in the DB schema