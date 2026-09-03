"""
embeddings.py
Turns skill text into a 768-dimension vector using Gemini's embedding
model. Call this ONCE per skill/requirement when it's first created,
then store the result (skill_embedding column) — never recompute it
on every match request.
"""

try:
    from .config import client, EMBEDDING_MODEL, EMBEDDING_DIM
except ImportError:
    from config import client, EMBEDDING_MODEL, EMBEDDING_DIM


def generate_embedding(text: str) -> list[float]:
    """
    Generates a single embedding vector for a piece of text
    (e.g. a skill name, or a whole project description).
    """
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config={"output_dimensionality": EMBEDDING_DIM},
    )
    return response.embeddings[0].values


def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """
    Same as generate_embedding but for many texts at once — use this
    when embedding a whole list of extracted skills together, it's
    faster than calling generate_embedding() in a loop.
    """
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config={"output_dimensionality": EMBEDDING_DIM},
    )
    return [e.values for e in response.embeddings]


if __name__ == "__main__":
    # Quick manual test — run `python embeddings.py`
    vec = generate_embedding("Python")
    print(f"Vector length: {len(vec)}")
    print(f"First 5 values: {vec[:5]}")