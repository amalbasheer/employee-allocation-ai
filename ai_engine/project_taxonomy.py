"""
project_taxonomy.py
Defines the business rules for project types — which broader category
each one belongs to, and which roles a project of that type actually
needs staffed.

NOTE: TM's seed data/UI currently store subject domain in project_type
(e.g. "Data Analytics", "Machine Learning") rather than engagement type
(batch/workshop/webinar/seminar/internal_project). Until that's resolved,
anything unrecognized defaults to "work_engagement" instead of crashing.
"""

PROJECT_TYPE_CATEGORY = {
    "batch":            "training_engagement",
    "workshop":         "training_engagement",
    "webinar":          "training_engagement",
    "seminar":          "training_engagement",
    "demo":             "training_engagement",
    "internal_project": "work_engagement",
}

CATEGORY_REQUIRED_ROLES = {
    "training_engagement": ["mentor"],
    "work_engagement":     ["team_lead", "intern"],
}

DEFAULT_CATEGORY = "work_engagement"


def get_category(project_type: str) -> str:
    category = PROJECT_TYPE_CATEGORY.get(project_type.lower())
    if category is None:
        return DEFAULT_CATEGORY
    return category


def get_required_roles(project_type: str) -> list[str]:
    category = get_category(project_type)
    return CATEGORY_REQUIRED_ROLES[category]


def needs_interns(project_type: str) -> bool:
    return "intern" in get_required_roles(project_type)