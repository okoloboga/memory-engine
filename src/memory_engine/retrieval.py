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


def hybrid_score(lexical_score: float | None, semantic_score: float | None) -> float:
    lex = lexical_score if lexical_score is not None else 0.0
    sem = semantic_score if semantic_score is not None else 0.0
    # lexical signal is sparse and strong for explicit intent; semantic for latent intent
    # normalize lexical into 0..1-ish band with cap
    lex_norm = min(lex / 3.0, 1.0)
    return (0.45 * lex_norm) + (0.55 * sem)


def dedup_key(atom: dict) -> str:
    summary = (atom.get("summary") or "").strip().lower()
    return f"{atom.get('type','')}::{summary}"
