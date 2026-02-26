from datetime import datetime, timezone
from pathlib import Path


def build_weekly_markdown(atoms: list[dict], limit: int = 10) -> str:
    ranked = sorted(atoms, key=lambda a: a.get("confidence", 0), reverse=True)[:limit]
    now = datetime.now(timezone.utc)
    year, week, _ = now.isocalendar()

    lines = [f"# Weekly Summary: {year}-W{week:02d}", ""]
    for a in ranked:
        lines.append(
            f"- [{a['type']}] {a['summary']} "
            f"[src: {a['source_file']}:{a['source_line_start']}-{a['source_line_end']}, conf: {a.get('confidence', 0):.2f}]"
        )
    lines.append("")
    return "\n".join(lines)


def save_weekly(markdown_text: str, out_dir: str = "data/runtime/weekly") -> Path:
    now = datetime.now(timezone.utc)
    year, week, _ = now.isocalendar()
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    out = target / f"{year}-W{week:02d}.md"
    out.write_text(markdown_text, encoding="utf-8")
    return out
