from pathlib import Path
import json


def save_atoms(atoms: list[dict], out_dir: str = "data/runtime", replace_sources: set[str] | None = None) -> tuple[Path, dict]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    path = target / "atoms.json"

    existing = []
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))

    removed = 0
    if replace_sources:
        filtered = []
        for a in existing:
            if a.get("source_file") in replace_sources:
                removed += 1
                continue
            filtered.append(a)
        existing = filtered

    by_id = {a["id"]: a for a in existing}
    for atom in atoms:
        by_id[atom["id"]] = atom

    merged = list(by_id.values())
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    stats = {
        "added": len(atoms),
        "removed": removed,
        "total": len(merged),
    }
    return path, stats


def save_embeddings(vectors: list[list[float]], atom_ids: list[str], out_dir: str = "data/runtime") -> Path:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    path = target / "embeddings.json"

    rows = [{"id": i, "vector": v} for i, v in zip(atom_ids, vectors)]
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return path
