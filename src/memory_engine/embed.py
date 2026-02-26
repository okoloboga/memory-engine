import httpx

from .config import settings


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not settings.comet_api_key or not texts:
        return []

    payload = {
        "model": settings.embed_model,
        "input": texts,
    }
    headers = {
        "Authorization": f"Bearer {settings.comet_api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        resp = client.post(settings.embed_url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    rows = data.get("data", [])
    return [row.get("embedding", []) for row in rows]
