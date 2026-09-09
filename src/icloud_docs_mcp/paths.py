"""Path helpers. User-facing paths never contain '..'."""

from __future__ import annotations

from icloud_docs_mcp.errors import ICloudError

FOLDER_TYPES = {"folder", "app_library"}


def sanitize_username(username: str) -> str:
    """Filesystem-safe token derived from an Apple ID."""
    cleaned = "".join(ch.lower() for ch in username if ch.isalnum())
    return cleaned or "account"


def normalize_relpath(path: str | None) -> str:
    """Return a relative Drive path with no parent-directory segments."""
    if path is None:
        return ""
    parts: list[str] = []
    for part in str(path).replace("\\", "/").split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise ICloudError("INVALID_PATH", "Parent path segments are not allowed")
        parts.append(part)
    return "/".join(parts)


def join_relpath(*parts: str) -> str:
    chunks: list[str] = []
    for part in parts:
        normalized = normalize_relpath(part)
        if normalized:
            chunks.append(normalized)
    return "/".join(chunks)


def normalize_ext(ext: str | None) -> str | None:
    if not ext:
        return None
    value = ext.strip().lower()
    if not value:
        return None
    if not value.startswith("."):
        value = f".{value}"
    return value


def name_matches(name: str, relpath: str, query: str, ext: str | None) -> bool:
    blob = f"{relpath}/{name}".lower() if relpath else name.lower()
    if query and query.lower() not in blob:
        return False
    suffix = normalize_ext(ext)
    if suffix and not name.lower().endswith(suffix):
        return False
    return True
