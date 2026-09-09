"""
optimizer.py

PuLP-based workload optimization.

Unlike matching.py (which ranks candidates for ONE project), this solves
allocation across MULTIPLE open projects at once so the same mentor isn't
assigned to every project.

Maximizes total suitability score across all assignments, subject to:
    - each project gets at most one mentor
    - mentors do not exceed the maximum allowed active projects
"""

import pulp

# Business rule (can later move to config.py if needed)
MAX_ACTIVE_PROJECTS = 2


def optimize_allocations(
    projects: list[dict],
    candidates: list[dict],
    score_matrix: dict[tuple[str, str], float],
) -> list[dict]:
    """
    Args:
        projects:
            [{"project_id": ...}, ...]

        candidates:
            [{
                "id": ...,
                "active_project_count": int
            }, ...]

        score_matrix:
            {(project_id, candidate_id): suitability_score}

    Returns:
        [
            {
                "project_id": ...,
                "candidate_id": ...,
                "score": ...
            }
        ]
    """

    prob = pulp.LpProblem("WorkforceAllocation", pulp.LpMaximize)

    # Binary decision variable for every valid project-candidate pair
    x = {
        (p_id, c_id): pulp.LpVariable(f"x_{p_id}_{c_id}", cat="Binary")
        for (p_id, c_id) in score_matrix
    }

    # Objective: maximize total suitability score
    prob += pulp.lpSum(
        score_matrix[pair] * x[pair]
        for pair in x
    )

    # ---------------------------------------------------------
    # Constraint 1:
    # Each project gets at most ONE mentor
    # ---------------------------------------------------------
    for project in projects:
        p_id = project["project_id"]

        relevant_vars = [
            x[pair]
            for pair in x
            if pair[0] == p_id
        ]

        if relevant_vars:
            prob += pulp.lpSum(relevant_vars) <= 1

    # ---------------------------------------------------------
    # Constraint 2:
    # Mentor cannot exceed maximum active projects
    # ---------------------------------------------------------
    for candidate in candidates:

        c_id = candidate["id"]

        active_projects = candidate.get(
            "active_project_count",
            0
        )

        remaining_slots = max(
            0,
            MAX_ACTIVE_PROJECTS - active_projects
        )

        relevant_pairs = [
            pair
            for pair in x
            if pair[1] == c_id
        ]

        if relevant_pairs:
            prob += (
                pulp.lpSum(
                    x[pair]
                    for pair in relevant_pairs
                )
                <= remaining_slots
            )

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    results = []

    for (p_id, c_id), var in x.items():

        if var.value() == 1:

            results.append(
                {
                    "project_id": p_id,
                    "candidate_id": c_id,
                    "score": score_matrix[(p_id, c_id)],
                }
            )

    return results


def build_score_matrix(
    projects_with_ranked_candidates: dict[str, list[dict]],
    min_score: float = 40.0,
) -> dict:

    matrix = {}

    for project_id, ranked_candidates in projects_with_ranked_candidates.items():

        for c in ranked_candidates:

            if c["suitability_score"] >= min_score:

                matrix[(project_id, c["id"])] = c["suitability_score"]

    return matrix


if __name__ == "__main__":

    fake_projects = [
        {"project_id": "p1"},
        {"project_id": "p2"},
    ]

    fake_candidates = [
        {
            "id": "alice",
            "active_project_count": 1,
        },
        {
            "id": "bob",
            "active_project_count": 0,
        },
    ]

    fake_scores = {
        ("p1", "alice"): 95,
        ("p1", "bob"): 90,
        ("p2", "alice"): 94,
        ("p2", "bob"): 88,
    }

    assignments = optimize_allocations(
        fake_projects,
        fake_candidates,
        fake_scores,
    )

    print(assignments)