from pathlib import Path
from dataclasses import dataclass


@dataclass
class ValidationIssue:
    atom_id: str
    issue: str


def validate_atoms_sources(atoms: list[dict]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for atom in atoms:
      aid = atom.get("id", "unknown")
      file = atom.get("source_file")
      start = int(atom.get("source_line_start", 0))
      end = int(atom.get("source_line_end", 0))
      summary = (atom.get("summary") or "").strip()

      if not file or start <= 0 or end < start:
          issues.append(ValidationIssue(aid, "invalid_source_range"))
          continue

      p = Path(file)
      if not p.exists():
          issues.append(ValidationIssue(aid, "source_file_missing"))
          continue

      lines = p.read_text(encoding="utf-8").splitlines()
      if end > len(lines):
          issues.append(ValidationIssue(aid, "source_range_out_of_bounds"))
          continue

      excerpt = "\n".join(lines[start - 1 : end]).lower()
      overlap = any(tok in excerpt for tok in summary.lower().split() if len(tok) > 3)
      if not overlap:
          issues.append(ValidationIssue(aid, "summary_not_grounded"))
    return issues
