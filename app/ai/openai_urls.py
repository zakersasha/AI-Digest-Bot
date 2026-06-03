OPENAI_DEFAULT_BASE_URL = "https://api.openai.com/v1"


def resolve_openai_base_url(base_url: str | None) -> str:
    if base_url and base_url.strip():
        return base_url.strip().rstrip("/")
    return OPENAI_DEFAULT_BASE_URL
