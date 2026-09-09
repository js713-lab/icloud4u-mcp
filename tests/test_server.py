from pathlib import Path

from icloud_docs_mcp.client import DriveClient
from icloud_docs_mcp.config import Settings
from icloud_docs_mcp.server import configure, list_folder, search, status
from tests.test_client import _tree
from types import SimpleNamespace


def test_tools_return_ok_json(tmp_path: Path):
    settings = Settings(
        username="you@example.com",
        password=None,
        session_dir=tmp_path / "session",
        download_dir=tmp_path / "downloads",
        root="",
    )
    api = SimpleNamespace(
        drive=_tree(),
        requires_2fa=False,
        requires_2sa=False,
        is_trusted_session=True,
    )
    configure(settings, DriveClient(settings, api=api))
    health = status()
    assert health["ok"] is True
    assert health["drive_reachable"] is True
    listed = list_folder("")
    assert listed["ok"] is True
    assert listed["count"] == 2
    found = search(query="budget")
    assert found["ok"] is True
    assert found["items"][0]["name"] == "Budget 2024.pdf"
