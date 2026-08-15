"""
optimizer.py
PuLP-based workload optimization. Unlike matching.py (which ranks
candidates for ONE project), this solves allocation across MULTIPLE
open projects at once — so a highly-rated mentor doesn't get
over-assigned to every project just because they scored well on all
of them individually.

Maximizes total suitability score across all assignments, subject to:
  - each project gets at most one candidate from this pass
  - no candidate is assigned more total hours than their weekly capacity
"""

import pulp


def optimize_allocations(
    projects: list[dict],
    candidates: list[dict],
    score_matrix: dict[tuple[str, str], float],
) -> list[dict]:
    """
    Args:
        projects: [{"project_id": ..., "required_hours_per_week": int}, ...]
        candidates: [{"id": ..., "weekly_capacity_hours": int, "already_allocated_hours": int}, ...]
        score_matrix: {(project_id, candidate_id): suitability_score, ...}
                      — build this by running matching.py's rank_candidates()
                      for each project first, then flattening into this dict.
                      Pairs below your quality threshold shouldn't be included
                      at all (keeps the problem smaller and avoids bad matches).

    Returns:
        [{"project_id": ..., "candidate_id": ..., "score": ...}, ...]
        — the optimal set of assignments. A project with no acceptable
        candidate simply won't appear in the results (stays unstaffed
        this round, worth flagging to an admin).
    """
    prob = pulp.LpProblem("WorkforceAllocation", pulp.LpMaximize)

    # One binary decision variable per (project, candidate) pair that
    # actually has a score — no variable created for pairs we excluded
    x = {
        (p_id, c_id): pulp.LpVariable(f"x_{p_id}_{c_id}", cat="Binary")
        for (p_id, c_id) in score_matrix
    }

    # Objective: maximize total suitability across all assignments made
    prob += pulp.lpSum(score_matrix[pair] * x[pair] for pair in x)

    # Constraint 1: each project gets AT MOST one candidate this round
    for project in projects:
        p_id = project["project_id"]
        relevant_vars = [x[pair] for pair in x if pair[0] == p_id]
        if relevant_vars:
            prob += pulp.lpSum(relevant_vars) <= 1

    # Constraint 2: no candidate exceeds their remaining weekly capacity
    hours_lookup = {p["project_id"]: p["required_hours_per_week"] for p in projects}
    for candidate in candidates:
        c_id = candidate["id"]
        remaining_capacity = (
            candidate["weekly_capacity_hours"] - candidate.get("already_allocated_hours", 0)
        )
        relevant_pairs = [pair for pair in x if pair[1] == c_id]
        if relevant_pairs:
            prob += pulp.lpSum(
                hours_lookup[pair[0]] * x[pair] for pair in relevant_pairs
            ) <= remaining_capacity

    prob.solve(pulp.PULP_CBC_CMD(msg=0))  # msg=0 silences solver logs

    results = []
    for (p_id, c_id), var in x.items():
        if var.value() == 1:
            results.append({
                "project_id": p_id,
                "candidate_id": c_id,
                "score": score_matrix[(p_id, c_id)],
            })

    return results


def build_score_matrix(projects_with_ranked_candidates: dict[str, list[dict]], min_score: float = 40.0) -> dict:
    """
    Helper to flatten matching.py's per-project rank_candidates() output
    into the score_matrix shape optimize_allocations() needs.

    Args:
        projects_with_ranked_candidates: {project_id: [ranked candidate dicts from matching.py], ...}
        min_score: candidates below this suitability score aren't even
                    considered — keeps the optimizer from ever proposing
                    a genuinely bad match just to fill a slot.

    Returns:
        {(project_id, candidate_id): score, ...}
    """
    matrix = {}
    for project_id, ranked_candidates in projects_with_ranked_candidates.items():
        for c in ranked_candidates:
            if c["suitability_score"] >= min_score:
                matrix[(project_id, c["id"])] = c["suitability_score"]
    return matrix


if __name__ == "__main__":
    # Quick manual test — two projects competing for the same top candidate
    fake_projects = [
        {"project_id": "p1", "required_hours_per_week": 10},
        {"project_id": "p2", "required_hours_per_week": 15},
    ]
    fake_candidates = [
        {"id": "alice", "weekly_capacity_hours": 20, "already_allocated_hours": 0},
        {"id": "ben", "weekly_capacity_hours": 20, "already_allocated_hours": 0},
    ]
    # Alice is the best fit for BOTH projects, but can't do both within her hours —
    # optimizer should split them instead of leaving p2 unstaffed
    fake_scores = {
        ("p1", "alice"): 95.0, ("p1", "ben"): 60.0,
        ("p2", "alice"): 90.0, ("p2", "ben"): 55.0,
    }

    assignments = optimize_allocations(fake_projects, fake_candidates, fake_scores)
    for a in assignments:
        print(a)