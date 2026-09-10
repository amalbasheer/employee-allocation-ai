import importlib

try:
    pulp = importlib.import_module("pulp")
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "PuLP is required for workload optimization. "
        "Install it with: python -m pip install pulp"
    ) from exc

MAX_ACTIVE_PROJECTS = 2


def optimize_allocations(
    projects: list[dict],
    candidates: list[dict],
    score_matrix: dict[tuple[str, str], float],
    time_limit_seconds: int = 3,
) -> list[dict]:
    """
    Solves workforce allocation using PuLP MIP solver.
    """
    if not score_matrix or not projects:
        return []

    prob = pulp.LpProblem("WorkforceAllocation", pulp.LpMaximize)

    # 1. Decision variables & O(1) indexed variable lookup groups
    x = {}
    project_vars = {p["project_id"]: [] for p in projects}
    candidate_vars = {c["id"]: [] for c in candidates}

    for (p_id, c_id), score in score_matrix.items():
        var = pulp.LpVariable(f"x_{p_id}_{c_id}", cat="Binary")
        x[(p_id, c_id)] = var
        if p_id in project_vars:
            project_vars[p_id].append(var)
        if c_id in candidate_vars:
            candidate_vars[c_id].append(var)

    # Objective: maximize total suitability score
    prob += pulp.lpSum(score_matrix[pair] * x[pair] for pair in x)

    # ---------------------------------------------------------
    # Constraint 1: Each project gets at most ONE mentor
    # ---------------------------------------------------------
    for p_id, vars_list in project_vars.items():
        if vars_list:
            prob += pulp.lpSum(vars_list) <= 1

    # ---------------------------------------------------------
    # Constraint 2: Mentor cannot exceed maximum active projects
    # ---------------------------------------------------------
    for candidate in candidates:
        c_id = candidate["id"]
        vars_list = candidate_vars.get(c_id, [])
        if not vars_list:
            continue

        active_projects = candidate.get("active_project_count", 0)
        remaining_slots = max(0, MAX_ACTIVE_PROJECTS - active_projects)
        prob += pulp.lpSum(vars_list) <= remaining_slots

    # Solve with a tight time limit to prevent web request timeouts
    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=time_limit_seconds)
    prob.solve(solver)

    results = []
    for (p_id, c_id), var in x.items():
        val = var.value()
        # Check against float precision tolerance (> 0.5 instead of == 1)
        if val is not None and val > 0.5:
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
            if c.get("suitability_score", 0) >= min_score:
                matrix[(project_id, c["id"])] = c["suitability_score"]
    return matrix


if __name__ == "__main__":
    fake_projects = [{"project_id": "p1"}, {"project_id": "p2"}]
    fake_candidates = [
        {"id": "alice", "active_project_count": 1},
        {"id": "bob", "active_project_count": 0},
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