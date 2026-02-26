from pathlib import Path
import json
import typer
from rich import print

from .parser import parse_markdown
from .config import settings
from .extractor import extract_atoms
from .store import save_atoms, save_embeddings
from .embed import embed_texts
from .validator import validate_atoms_sources
from .weekly import build_weekly_markdown, save_weekly
from .retrieval import semantic_rank, hybrid_score, dedup_key

app = typer.Typer(help="Memory Engine CLI")


@app.command()
def ingest(path: str, extract: bool = typer.Option(True, help="Run LLM extraction"), embed: bool = typer.Option(True, help="Build embeddings")):
    """Parse markdown file/folder into chunks; optionally extract atoms + embeddings."""
    p = Path(path)
    files = [p] if p.is_file() else sorted(p.rglob("*.md"))
    chunks = []
    for f in files:
        chunks.extend(parse_markdown(str(f)))

    out_dir = Path("data/runtime")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "chunks.json"
    out_file.write_text(json.dumps([c.model_dump() for c in chunks], ensure_ascii=False, indent=2), encoding="utf-8")

    atoms: list[dict] = []
    if extract:
        for chunk in chunks:
            try:
                atoms.extend(extract_atoms(chunk))
            except Exception as e:
                print(f"[yellow]extract warning[/yellow] {chunk.file}:{chunk.line_start}-{chunk.line_end} -> {e}")
        atoms_path = save_atoms(atoms, out_dir=str(out_dir))
        print(f"[cyan]Atoms[/cyan]: {len(atoms)} -> {atoms_path}")

        issues = validate_atoms_sources(atoms)
        if issues:
            print(f"[yellow]Validation issues[/yellow]: {len(issues)}")
            for i in issues[:10]:
                print(f"  - {i.atom_id}: {i.issue}")
        else:
            print("[green]Validation[/green]: all atoms grounded to sources")

        if embed and atoms:
            vectors = embed_texts([a["summary"] for a in atoms])
            emb_path = save_embeddings(vectors, [a["id"] for a in atoms], out_dir=str(out_dir))
            print(f"[cyan]Embeddings[/cyan]: {len(vectors)} -> {emb_path}")

    print(f"[green]Ingested[/green] {len(files)} files, {len(chunks)} chunks -> {out_file}")


@app.command()
def query(text: str, top_k: int = 5):
    """Hybrid-lite retrieval: lexical + semantic (if embeddings available)."""
    atoms_path = Path("data/runtime/atoms.json")
    if not atoms_path.exists():
        print("No atoms found. Run ingest first.")
        raise typer.Exit(code=1)

    atoms = json.loads(atoms_path.read_text(encoding="utf-8"))
    atoms_by_id = {a["id"]: a for a in atoms if "id" in a}
    q = text.lower().strip()

    # lexical branch
    lexical = []
    for a in atoms:
        hay = f"{a.get('summary', '')} {' '.join(a.get('tags', []))}".lower()
        score = sum(1 for token in q.split() if token in hay)
        if score > 0:
            lexical.append((float(score), a))

    lexical.sort(key=lambda x: x[0], reverse=True)

    # semantic branch
    semantic: list[tuple[float, dict]] = []
    emb_path = Path("data/runtime/embeddings.json")
    try:
        if emb_path.exists():
            qv = embed_texts([text])
            if qv:
                emb_rows = json.loads(emb_path.read_text(encoding="utf-8"))
                semantic = semantic_rank(qv[0], emb_rows, atoms_by_id, top_k=top_k)
    except Exception as e:
        print(f"[yellow]semantic warning[/yellow] {e}")

    # merge + hybrid score + content dedup
    merged: dict[str, tuple[float | None, float | None, dict, str]] = {}
    for s, a in lexical:
        merged[a["id"]] = (s, None, a, "lex")
    for s, a in semantic:
        prev = merged.get(a["id"])
        if prev:
            merged[a["id"]] = (prev[0], s, a, "hybrid")
        else:
            merged[a["id"]] = (None, s, a, "sem")

    rows: list[tuple[float, dict, str]] = []
    for lex_s, sem_s, atom, mode in merged.values():
        rows.append((hybrid_score(lex_s, sem_s), atom, mode))

    rows.sort(key=lambda x: x[0], reverse=True)

    deduped: list[tuple[float, dict, str]] = []
    seen = set()
    for score, atom, mode in rows:
        key = dedup_key(atom)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((score, atom, mode))
        if len(deduped) >= top_k:
            break

    for score, a, mode in deduped:
        print(
            f"- ({score:.3f},{mode}) [{a['type']}] {a['summary']} "
            f"[src: {a['source_file']}:{a['source_line_start']}-{a['source_line_end']}]"
        )

    ranked = deduped

    if not ranked:
        print("No hits yet. Run ingest with extraction first.")


@app.command()
def weekly(limit: int = 10):
    """Draft weekly summary from current atoms (source-first)."""
    atoms_path = Path("data/runtime/atoms.json")
    if not atoms_path.exists():
        print("No atoms found. Run ingest first.")
        raise typer.Exit(code=1)

    atoms = json.loads(atoms_path.read_text(encoding="utf-8"))
    issues = validate_atoms_sources(atoms)
    if issues:
        bad = {i.atom_id for i in issues}
        atoms = [a for a in atoms if a.get("id") not in bad]
        print(f"Filtered out {len(bad)} ungrounded atoms before weekly")

    md = build_weekly_markdown(atoms, limit=limit)
    print(md)
    path = save_weekly(md)
    print(f"Saved weekly -> {path}")

    print(f"\nConfigured extraction model: {settings.extraction_model}")
    print(f"Configured embedding model: {settings.embed_model}")


if __name__ == "__main__":
    app()
