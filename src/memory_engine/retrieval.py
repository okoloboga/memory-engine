import math


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def semantic_rank(query_vec: list[float], emb_rows: list[dict], atoms_by_id: dict[str, dict], top_k: int = 5) -> list[tuple[float, dict]]:
    scored: list[tuple[float, dict]] = []
    for row in emb_rows:
        aid = row.get("id")
        vec = row.get("vector", [])
        atom = atoms_by_id.get(aid)
        if not atom:
            continue
        score = cosine(query_vec, vec)
        if score > 0:
            scored.append((score, atom))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]
