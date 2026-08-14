"""
matching.py
Core matching logic: given a set of skill embeddings for a project
and a set of candidates (each with their own skill embeddings),
rank the candidates by similarity.
"""

import numpy as np


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Returns a similarity score between -1 and 1 (in practice usually
    0 to 1 for embeddings) — higher means more semantically similar.
    """
    a = np.array(vec_a)
    b = np.array(vec_b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def score_candidate(candidate_skills: list[dict], project_requirements: list[dict]) -> float:
    """
    Scores one candidate against one project's full requirement list.
    Returns a 0-100 suitability score. Mandatory requirements that
    aren't met pull the score down harder than optional ones.
    """
    if not project_requirements:
        return 0.0

    total_weight = 0.0
    weighted_score = 0.0

    for req in project_requirements:
        # Find the candidate's best-matching skill for this requirement
        best_sim = 0.0
        best_skill = None
        for skill in candidate_skills:
            sim = cosine_similarity(skill["embedding"], req["embedding"])
            if sim > best_sim:
                best_sim = sim
                best_skill = skill

        # Check proficiency threshold on the best match
        meets_proficiency = (
            best_skill is not None
            and best_skill.get("proficiency_level", 0) >= req.get("min_proficiency", 1)
        )

        # Mandatory requirements are weighted 2x — missing one hurts more
        weight = 2.0 if req.get("is_mandatory", True) else 1.0
        requirement_score = best_sim * (1.0 if meets_proficiency else 0.5)

        weighted_score += requirement_score * weight
        total_weight += weight

    return round((weighted_score / total_weight) * 100, 2)


def rank_candidates(candidates: list[dict], project_requirements: list[dict]) -> list[dict]:
    """
    Ranks every candidate against one project's requirements, highest
    suitability first. Returns the same dicts with a "suitability_score" added.
    """
    scored = []
    for c in candidates:
        score = score_candidate(c["skills"], project_requirements)
        scored.append({**c, "suitability_score": score})

    return sorted(scored, key=lambda c: c["suitability_score"], reverse=True)


if __name__ == "__main__":
    # Quick manual test with fake vectors
    fake_requirements = [
        {"skill_id": "s1", "embedding": [1, 0, 0], "min_proficiency": 3, "is_mandatory": True},
        {"skill_id": "s2", "embedding": [0, 1, 0], "min_proficiency": 2, "is_mandatory": False},
    ]

    fake_candidates = [
        {
            "id": "c1", "name": "Alice", "available_hours": 10,
            "skills": [
                {"skill_id": "s1", "embedding": [0.9, 0.1, 0], "proficiency_level": 4},
                {"skill_id": "s2", "embedding": [0.1, 0.9, 0], "proficiency_level": 3},
            ],
        },
        {
            "id": "c2", "name": "Ben", "available_hours": 5,
            "skills": [
                {"skill_id": "s1", "embedding": [0.5, 0.5, 0], "proficiency_level": 2},
            ],
        },
    ]

    ranked = rank_candidates(fake_candidates, fake_requirements)
    for r in ranked:
        print(f"{r['name']}: {r['suitability_score']}")