"""Environment-only settings. No default Apple ID or password."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from icloud_docs_mcp.errors import ICloudError
from icloud_docs_mcp.paths import normalize_relpath, sanitize_username

APP_NAME = "icloud-docs-mcp"


def _xdg_home(env_name: str, fallback: Path) -> Path:
    raw = os.environ.get(env_name, "").strip()
    if raw:
        return Path(raw).expanduser()
    return fallback


def data_home() -> Path:
    return _xdg_home("XDG_DATA_HOME", Path.home() / ".local" / "share")


def cache_home() -> Path:
    return _xdg_home("XDG_CACHE_HOME", Path.home() / ".cache")


def load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE pairs from a local .env if present. Existing env wins."""
    env_path = path or Path.cwd() / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    username: str | None
    password: str | None
    session_dir: Path
    download_dir: Path
    root: str

    def require_username(self) -> str:
        if not self.username:
            raise ICloudError(
                "CONFIG",
                "Set ICLOUD_USERNAME to your Apple ID. There is no default.",
            )
        return self.username


def default_session_dir(username: str | None) -> Path:
    token = sanitize_username(username or "default")
    return data_home() / APP_NAME / token


def default_download_dir(username: str | None) -> Path:
    token = sanitize_username(username or "default")
    return cache_home() / APP_NAME / token / "downloads"


def load_settings() -> Settings:
    username = os.environ.get("ICLOUD_USERNAME", "").strip() or None
    password = os.environ.get("ICLOUD_PASSWORD")
    if password is not None and password == "":
        password = None

    session_override = os.environ.get("ICLOUD_SESSION_DIR", "").strip()
    download_override = os.environ.get("ICLOUD_DOWNLOAD_DIR", "").strip()
    root = normalize_relpath(os.environ.get("ICLOUD_ROOT", "").strip())

    session_dir = (
        Path(session_override).expanduser()
        if session_override
        else default_session_dir(username)
    )
    download_dir = (
        Path(download_override).expanduser()
        if download_override
        else default_download_dir(username)
    )
    return Settings(
        username=username,
        password=password,
        session_dir=session_dir,
        download_dir=download_dir,
        root=root,
    )
