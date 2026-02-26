# Memory Engine MVP

Personal memory engine project (MVP).

## Commands

- `memory ingest <path>` — parse markdown sources into chunks
- `memory query <text>` — placeholder retrieval command
- `memory weekly` — placeholder weekly summary command

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

## Security

- Keep API keys only in `.env`
- Never commit secrets
