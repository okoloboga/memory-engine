# Memory Engine MVP

Personal memory engine project (MVP).

## Commands

- `memory ingest <path>` — parse markdown, extract atoms, build embeddings
- `memory query <text>` — hybrid-lite retrieval (lexical + semantic)
- `memory weekly` — weekly summary with source filtering + claim check

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

## Quality checks

```bash
source .venv/bin/activate
pip install -e .[dev]
pytest -q
```

## Security

- Keep API keys only in `.env`
- Never commit secrets
