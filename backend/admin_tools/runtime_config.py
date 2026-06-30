import os


def default_project_id() -> str:
    env_project = (os.environ.get("ADMIN_TOOLS_PROJECT_ID") or "").strip()
    if env_project:
        return env_project

    raise RuntimeError(
        "Project ID is not configured. Set ADMIN_TOOLS_PROJECT_ID."
    )


def default_api_service() -> str:
    env_service = (os.environ.get("ADMIN_TOOLS_API_SERVICE") or "").strip()
    if env_service:
        return env_service

    raise RuntimeError(
        "API service is not configured. Set ADMIN_TOOLS_API_SERVICE."
    )
