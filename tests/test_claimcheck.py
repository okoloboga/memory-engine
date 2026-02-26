from memory_engine.claimcheck import claim_check_markdown


def test_claimcheck_keeps_only_sourced_lines():
    atoms = [
        {
            "source_file": "memory/2026-02-26.md",
            "source_line_start": 1,
            "source_line_end": 3,
        }
    ]
    md = "# Weekly\n- ok [src: memory/2026-02-26.md:1-3, conf: 0.9]\n- bad [src: memory/2026-02-26.md:5-9, conf: 0.7]\n"
    out, res = claim_check_markdown(md, atoms)
    assert "- ok" in out
    assert "- bad" not in out
    assert res.verified == 1
    assert res.dropped == 1
