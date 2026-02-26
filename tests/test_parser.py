from pathlib import Path
from memory_engine.parser import parse_markdown


def test_parse_markdown_tracks_lines(tmp_path: Path):
    p = tmp_path / "a.md"
    p.write_text("# T\n\n## One\na\n\n## Two\nb\n", encoding="utf-8")

    chunks = parse_markdown(str(p))
    assert len(chunks) >= 2
    assert chunks[0].line_start >= 1
    assert chunks[0].line_end >= chunks[0].line_start
