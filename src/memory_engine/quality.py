from collections import Counter


def quality_dashboard(atoms: list[dict], validation_issues: list, claim_total: int, claim_verified: int, claim_dropped: int, ingest_stats: dict | None = None) -> str:
    by_type = Counter(a.get("type", "unknown") for a in atoms)
    avg_conf = 0.0
    if atoms:
        avg_conf = sum(float(a.get("confidence", 0)) for a in atoms) / len(atoms)

    lines = [
        "## Quality Dashboard",
        f"- Atoms total: {len(atoms)}",
        f"- Avg confidence: {avg_conf:.2f}",
        f"- Validation issues: {len(validation_issues)}",
        f"- ClaimCheck: verified={claim_verified}/{claim_total}, dropped={claim_dropped}",
    ]
    if ingest_stats:
        lines.append(
            f"- Ingest stats: added={ingest_stats.get('added',0)}, removed={ingest_stats.get('removed',0)}, total={ingest_stats.get('total',len(atoms))}"
        )
    lines.append("- Atoms by type:")
    for t, n in sorted(by_type.items(), key=lambda x: x[0]):
        lines.append(f"  - {t}: {n}")
    return "\n".join(lines)
