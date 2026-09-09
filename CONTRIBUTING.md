# Contributing

## Setup

Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Tests mock Apple. Do not add CI jobs that log into iCloud or that read a real cookiejar.

## Secrets

Never commit:

- `.env` (keep `.env.example` empty of real values)
- cookiejar / session files
- downloaded Drive documents

The secrets test fails the build if tracked files look like machine paths, consumer email addresses, or hardcoded passwords.

## Pull requests

- Keep the server read-only unless a change is discussed first.
- Prefer small, tested diffs.
- Do not include live iCloud fixtures or personal documents.
