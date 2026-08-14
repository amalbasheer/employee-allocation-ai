"""
project_taxonomy.py
Defines the business rules for project types — which broader category
each one belongs to, and which roles a project of that type actually
needs staffed.
"""

# project_type -> category
PROJECT_TYPE_CATEGORY = {
    "batch":            "training_engagement",   # student batch
    "workshop":         "training_engagement",
    "webinar":          "training_engagement",
    "seminar":          "training_engagement",
    "demo":             "training_engagement",
    "internal_project":  "work_engagement",       # RP2 AI Labs project
}

# category -> which roles must be filled for a project of that category
CATEGORY_REQUIRED_ROLES = {
    "training_engagement": ["mentor"],
    "work_engagement":     ["team_lead", "intern"],
}


def get_category(project_type: str) -> str:
    category = PROJECT_TYPE_CATEGORY.get(project_type.lower())
    if category is None:
        raise ValueError(
            f"Unknown project_type '{project_type}'. "
            f"Known types: {list(PROJECT_TYPE_CATEGORY.keys())}"
        )
    return category


def get_required_roles(project_type: str) -> list[str]:
    category = get_category(project_type)
    return CATEGORY_REQUIRED_ROLES[category]


def needs_interns(project_type: str) -> bool:
    return "intern" in get_required_roles(project_type)


if __name__ == "__main__":
    for pt in ["batch", "workshop", "internal_project", "demo"]:
        print(f"{pt:20s} -> category: {get_category(pt):20s} roles: {get_required_roles(pt)}")