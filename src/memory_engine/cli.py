from pathlib import Path
import json
import typer
from rich import print

from .parser import parse_markdown
from .config import settings
from .extractor import extract_atoms
from .store import save_atoms, save_embeddings
from .embed import embed_texts

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

        if embed and atoms:
            vectors = embed_texts([a["summary"] for a in atoms])
            emb_path = save_embeddings(vectors, [a["id"] for a in atoms], out_dir=str(out_dir))
            print(f"[cyan]Embeddings[/cyan]: {len(vectors)} -> {emb_path}")

    print(f"[green]Ingested[/green] {len(files)} files, {len(chunks)} chunks -> {out_file}")


@app.command()
def query(text: str, top_k: int = 5):
    """Simple retrieval command over extracted atoms."""
    atoms_path = Path("data/runtime/atoms.json")
    if not atoms_path.exists():
        print("No atoms found. Run ingest first.")
        raise typer.Exit(code=1)

    atoms = json.loads(atoms_path.read_text(encoding="utf-8"))
    q = text.lower().strip()

    scored = []
    for a in atoms:
        hay = f"{a.get('summary', '')} {' '.join(a.get('tags', []))}".lower()
        score = sum(1 for token in q.split() if token in hay)
        if score > 0:
            scored.append((score, a))

    scored.sort(key=lambda x: x[0], reverse=True)
    for score, a in scored[:top_k]:
        print(f"- ({score}) [{a['type']}] {a['summary']} [src: {a['source_file']}:{a['source_line_start']}-{a['source_line_end']}]")

    if not scored:
        print("No lexical hits yet. (semantic retrieval next)")


@app.command()
def weekly(limit: int = 10):
    """Draft weekly summary from current atoms (source-first)."""
    atoms_path = Path("data/runtime/atoms.json")
    if not atoms_path.exists():
        print("No atoms found. Run ingest first.")
        raise typer.Exit(code=1)

    atoms = json.loads(atoms_path.read_text(encoding="utf-8"))
    ranked = sorted(atoms, key=lambda a: a.get("confidence", 0), reverse=True)[:limit]

    print("# Weekly Summary (draft)")
    for a in ranked:
        print(
            f"- [{a['type']}] {a['summary']} "
            f"[src: {a['source_file']}:{a['source_line_start']}-{a['source_line_end']}, conf: {a.get('confidence', 0):.2f}]"
        )

    print(f"\nConfigured extraction model: {settings.extraction_model}")
    print(f"Configured embedding model: {settings.embed_model}")


if __name__ == "__main__":
    app()
