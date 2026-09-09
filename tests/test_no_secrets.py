from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {
    ".venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".eggs",
    "dist",
    "build",
    "htmlcov",
    "icloud-docs-mcp.egg-info",
}
SCAN_SUFFIXES = {
    ".py",
    ".md",
    ".toml",
    ".txt",
    ".yml",
    ".yaml",
    ".example",
    ".gitignore",
    ".in",
}
SCAN_NAMES = {
    "LICENSE",
    ".gitignore",
    ".env.example",
}

# Generic leak patterns only. Do not encode personal names or private hostnames.
FORBIDDEN = [
    re.compile(r"PASSWORD\s*=\s*['\"][^'\"]+['\"]"),
    re.compile(r"^[ \t]*ICLOUD_PASSWORD[ \t]*=[ \t]*\S+", re.M),
    re.compile(r"/home/[a-zA-Z0-9._-]+"),
    re.compile(r"/Users/[a-zA-Z0-9._-]+"),
    re.compile(r"/Desktop/"),
    re.compile(r"\bts\.net\b", re.I),
    re.compile(
        r"[a-zA-Z0-9._%+-]+@(?:gmail|icloud|me|mac|outlook|hotmail|yahoo)\.[a-z]{2,}",
        re.I,
    ),
]


def _files() -> list[Path]:
    found: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.name == "test_no_secrets.py":
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in SCAN_SUFFIXES and path.name not in SCAN_NAMES:
            continue
        found.append(path)
    return found


def test_source_has_no_credentials_or_machine_paths():
    hits: list[str] = []
    for path in _files():
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN:
            if pattern.search(text):
                hits.append(f"{path.relative_to(ROOT)}: {pattern.pattern}")
    assert hits == []


MUST_IGNORE = [
    ".env",
    ".env.local",
    ".env.production",
    "local.env",
    "session/account.cookiejar",
    "session/account.session",
    "cookies/account.cookiejar",
    "account.cookiejar",
    "account.session",
    "downloads/file.pdf",
    "cookies.txt",
    "id_rsa",
    "id_ed25519",
    "cert.pem",
    "auth.p12",
    "secrets.yaml",
    "credentials.json",
]


def test_gitignore_covers_secret_filenames():
    listed = subprocess.run(
        ["git", "-C", str(ROOT), "check-ignore", "--stdin"],
        input="\n".join(MUST_IGNORE) + "\n",
        capture_output=True,
        text=True,
        check=False,
    )
    ignored = {line for line in listed.stdout.splitlines() if line}
    missing = [path for path in MUST_IGNORE if path not in ignored]
    assert missing == [], f"gitignore missed: {missing}"

    example = subprocess.run(
        ["git", "-C", str(ROOT), "check-ignore", ".env.example"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert example.returncode == 1, ".env.example must stay tracked"
