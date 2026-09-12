from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

from icloud_docs_mcp.client import DriveClient
from icloud_docs_mcp.config import Settings
from icloud_docs_mcp.errors import ICloudError
import pytest


class FakeFile:
    def __init__(self, name: str, content: bytes) -> None:
        self.name = name
        self.type = "file"
        self.size = len(content)
        self._content = content

    def open(self, stream: bool = True):
        payload = self._content

        class _Resp:
            raw = io.BytesIO(payload)
            content = payload

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return _Resp()


class FakeFolder:
    def __init__(self, name: str, children: list[object], node_type: str = "folder") -> None:
        self.name = name
        self.type = node_type
        self.size = None
        self._children = children

    def get_children(self):
        return self._children

    def dir(self):
        return [child.name for child in self._children]

    def __getitem__(self, key: str):
        for child in self._children:
            if child.name == key:
                return child
        raise KeyError(key)


def _settings(tmp_path: Path, root: str = "") -> Settings:
    return Settings(
        username="you@example.com",
        password=None,
        session_dir=tmp_path / "session",
        download_dir=tmp_path / "downloads",
        root=root,
    )


def _tree() -> FakeFolder:
    return FakeFolder(
        "root",
        [
            FakeFolder(
                "Documents",
                [
                    FakeFile("Budget 2024.pdf", b"%PDF-fake"),
                    FakeFile("notes.txt", b"hello"),
                    FakeFolder("Archive", [FakeFile("old.docx", b"PK")]),
                ],
            ),
            FakeFile("readme.md", b"# hi"),
        ],
    )


def _client(tmp_path: Path, root: str = "") -> DriveClient:
    api = SimpleNamespace(
        drive=_tree(),
        requires_2fa=False,
        requires_2sa=False,
        is_trusted_session=True,
    )
    client = DriveClient(_settings(tmp_path, root=root), api=api)
    client.connect()
    return client


def test_list_folder_one_level(tmp_path: Path):
    items = _client(tmp_path).list_folder("")
    names = [item.name for item in items]
    assert names == ["Documents", "readme.md"]
    nested = _client(tmp_path).list_folder("Documents")
    assert [item.name for item in nested] == ["Archive", "Budget 2024.pdf", "notes.txt"]


def test_search_by_query_and_ext(tmp_path: Path):
    items, truncated, visited = _client(tmp_path).search(query="budget", ext="pdf")
    assert truncated is False
    assert visited >= 1
    assert [item.path for item in items] == ["Documents/Budget 2024.pdf"]


def test_search_requires_query_or_ext(tmp_path: Path):
    with pytest.raises(ICloudError) as exc:
        _client(tmp_path).search(query="", ext="")
    assert exc.value.code == "INVALID_QUERY"


def test_download_and_read_text(tmp_path: Path):
    client = _client(tmp_path)
    results = client.download(["Documents/notes.txt"])
    assert results[0]["status"] == "downloaded"
    dest = Path(results[0]["dest"])
    assert dest.read_text(encoding="utf-8") == "hello"
    payload = client.read_text("Documents/notes.txt")
    assert payload["text"] == "hello"
    assert payload["truncated"] is False


def test_connect_restricts_session_and_download_dirs(tmp_path: Path):
    session = tmp_path / "session"
    downloads = tmp_path / "downloads"
    client = DriveClient(
        Settings(
            username="user@example.com",
            password=None,
            session_dir=session,
            download_dir=downloads,
            root="",
        )
    )
    # connect() fails NEED_LOGIN (no cookiejar / password) after mkdir+chmod,
    # without importing pyicloud.
    with pytest.raises(ICloudError) as exc:
        client.connect()
    assert exc.value.code == "NEED_LOGIN"
    assert session.is_dir()
    assert downloads.is_dir()
    session_mode = session.stat().st_mode & 0o777
    download_mode = downloads.stat().st_mode & 0o777
    assert session_mode & 0o007 == 0, f"session dir is world-accessible: {oct(session_mode)}"
    assert download_mode & 0o007 == 0, f"download dir is world-accessible: {oct(download_mode)}"


def test_icloud_root_scopes_paths(tmp_path: Path):
    client = _client(tmp_path, root="Documents")
    names = [item.name for item in client.list_folder("")]
    assert "Budget 2024.pdf" in names
    items, _, _ = client.search(query="notes")
    assert [item.path for item in items] == ["notes.txt"]


def test_missing_username(tmp_path: Path):
    settings = Settings(
        username=None,
        password=None,
        session_dir=tmp_path / "session",
        download_dir=tmp_path / "downloads",
        root="",
    )
    client = DriveClient(settings)
    with pytest.raises(ICloudError) as exc:
        client.status()
    assert exc.value.code == "CONFIG"
