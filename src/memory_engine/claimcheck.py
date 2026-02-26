from dataclasses import dataclass


@dataclass
class ClaimCheckResult:
    total: int
    verified: int
    dropped: int


def claim_check_markdown(markdown_text: str, atoms: list[dict]) -> tuple[str, ClaimCheckResult]:
    """
    Very strict v1 checker:
    keep only bullet claims that have [src: file:start-end, conf: x.xx]
    and matching source tuple in atoms list.
    """
    valid_refs = {
        (a.get("source_file"), int(a.get("source_line_start", 0)), int(a.get("source_line_end", 0)))
        for a in atoms
        if a.get("source_file")
    }

    lines = markdown_text.splitlines()
    out: list[str] = []
    total = verified = dropped = 0

    for ln in lines:
        if not ln.strip().startswith("-"):
            out.append(ln)
            continue

        marker = "[src: "
        if marker not in ln:
            # non-claim bullet (e.g., dashboard line) - keep as-is
            out.append(ln)
            continue

        total += 1

        try:
            src_part = ln.split(marker, 1)[1].split(",", 1)[0].strip()
            # file:path:lineStart-lineEnd
            file_part, range_part = src_part.rsplit(":", 1)
            ls, le = range_part.split("-", 1)
            ref = (file_part, int(ls), int(le))
            if ref in valid_refs:
                out.append(ln)
                verified += 1
            else:
                dropped += 1
        except Exception:
            dropped += 1

    out.append("")
    out.append(f"ClaimCheck: verified={verified}/{total}, dropped={dropped}")
    return "\n".join(out), ClaimCheckResult(total=total, verified=verified, dropped=dropped)
