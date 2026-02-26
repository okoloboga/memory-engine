from pathlib import Path
import json
import typer
from rich import print

from .parser import parse_markdown
from .config import settings

app = typer.Typer(help="Memory Engine CLI")


@app.command()
def ingest(path: str):
    """Parse markdown file/folder into chunks."""
    p = Path(path)
    files = [p] if p.is_file() else sorted(p.rglob("*.md"))
    out = []
    for f in files:
        out.extend([c.model_dump() for c in parse_markdown(str(f))])

    out_dir = Path("data/runtime")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "chunks.json"
    out_file.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[green]Ingested[/green] {len(files)} files, {len(out)} chunks -> {out_file}")


@app.command()
def query(text: str):
    """Placeholder query command."""
    print(f"Query received: {text}")
    print("Retrieval layer: TODO")


@app.command()
def weekly():
    """Placeholder weekly summary command."""
    print("Weekly summary: TODO")
    print(f"Configured extraction model: {settings.extraction_model}")
    print(f"Configured embedding model: {settings.embed_model}")


if __name__ == "__main__":
    app()
