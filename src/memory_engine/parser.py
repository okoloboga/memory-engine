from pathlib import Path
from .models import Chunk


def parse_markdown(path: str) -> list[Chunk]:
    p = Path(path)
    lines = p.read_text(encoding="utf-8").splitlines()
    chunks: list[Chunk] = []

    start = 1
    buf: list[str] = []

    def flush(end_line: int):
        nonlocal start, buf
        text = "\n".join(buf).strip()
        if text:
            chunks.append(
                Chunk(
                    file=str(p),
                    line_start=start,
                    line_end=end_line,
                    text=text,
                )
            )

    for i, line in enumerate(lines, start=1):
        if line.startswith("## ") and buf:
            flush(i - 1)
            start = i
            buf = [line]
        else:
            if not buf:
                start = i
            buf.append(line)

    if buf:
        flush(len(lines))

    return chunks
