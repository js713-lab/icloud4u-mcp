from pathlib import Path

from icloud_docs_mcp.config import load_settings
from icloud_docs_mcp.errors import ICloudError
import pytest


def test_load_settings_has_no_default_username(monkeypatch, tmp_path):
    monkeypatch.delenv("ICLOUD_USERNAME", raising=False)
    monkeypatch.delenv("ICLOUD_PASSWORD", raising=False)
    monkeypatch.delenv("ICLOUD_SESSION_DIR", raising=False)
    monkeypatch.delenv("ICLOUD_DOWNLOAD_DIR", raising=False)
    monkeypatch.delenv("ICLOUD_ROOT", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    settings = load_settings()
    assert settings.username is None
    assert settings.password is None
    with pytest.raises(ICloudError) as exc:
        settings.require_username()
    assert exc.value.code == "CONFIG"


def test_load_settings_from_env(monkeypatch, tmp_path):
    session = tmp_path / "session"
    downloads = tmp_path / "downloads"
    monkeypatch.setenv("ICLOUD_USERNAME", "you@example.com")
    monkeypatch.setenv("ICLOUD_PASSWORD", "")
    monkeypatch.setenv("ICLOUD_SESSION_DIR", str(session))
    monkeypatch.setenv("ICLOUD_DOWNLOAD_DIR", str(downloads))
    monkeypatch.setenv("ICLOUD_ROOT", "/Documents/Work/")
    settings = load_settings()
    assert settings.username == "you@example.com"
    assert settings.password is None
    assert settings.session_dir == session
    assert settings.download_dir == downloads
    assert settings.root == "Documents/Work"


def test_dotenv_does_not_override_existing_env(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("ICLOUD_USERNAME=from-file@example.com\n", encoding="utf-8")
    monkeypatch.setenv("ICLOUD_USERNAME", "from-env@example.com")
    from icloud_docs_mcp.config import load_dotenv

    load_dotenv(env_file)
    assert Path(env_file).exists()
    from os import environ

    assert environ["ICLOUD_USERNAME"] == "from-env@example.com"
