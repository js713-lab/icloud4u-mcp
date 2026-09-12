"""Thin pyicloud Drive client. Read-only. No domain-specific classifiers."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from shutil import copyfileobj
from typing import Any, Iterable

from icloud_docs_mcp.config import Settings
from icloud_docs_mcp.errors import ICloudError
from icloud_docs_mcp.extract import extract_file
from icloud_docs_mcp.paths import (
    FOLDER_TYPES,
    join_relpath,
    name_matches,
    normalize_ext,
    normalize_relpath,
)

LOGGER = logging.getLogger(__name__)

DEFAULT_SEARCH_LIMIT = 30
MAX_SEARCH_LIMIT = 100
DEFAULT_MAX_VISITED = 3000
DEFAULT_MAX_DEPTH = 12


@dataclass
class DriveItem:
    path: str
    name: str
    type: str
    size: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "path": self.path,
            "name": self.name,
            "type": self.type,
        }
        if self.size is not None:
            payload["size"] = self.size
        if self.error:
            payload["error"] = self.error
        return payload


class DriveClient:
    def __init__(self, settings: Settings, api: Any | None = None) -> None:
        self.settings = settings
        self._api = api
        self._root_node: Any | None = None

    def connect(self) -> None:
        """Reuse a trusted cookiejar. Never prompt. Never request a 2FA code."""
        if self._api is not None:
            self._prepare_root()
            return

        username = self.settings.require_username()
        self._disable_keyring()
        self.settings.session_dir.mkdir(parents=True, exist_ok=True)
        self.settings.download_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.settings.session_dir, 0o700)
            os.chmod(self.settings.download_dir, 0o700)
        except OSError:
            LOGGER.warning("Could not restrict session/download directory permissions")

        from pyicloud import PyiCloudService
        from pyicloud.exceptions import (
            PyiCloudAPIResponseException,
            PyiCloudFailedLoginException,
        )

        has_session = any(self.settings.session_dir.iterdir())
        if not has_session and not self.settings.password:
            raise ICloudError(
                "NEED_LOGIN",
                "No local session. Run `icloud-docs-mcp login` in a terminal.",
            )

        try:
            api = PyiCloudService(
                username,
                self.settings.password,
                cookie_directory=str(self.settings.session_dir),
                accept_terms=True,
                authenticate=False,
            )
            api.authenticate()
        except ICloudError:
            raise
        except PyiCloudFailedLoginException as exc:
            raise ICloudError(
                "NEED_LOGIN",
                f"Login failed: {exc}. Run `icloud-docs-mcp login` in a terminal.",
            ) from exc
        except PyiCloudAPIResponseException as exc:
            raise ICloudError("UNAVAILABLE", f"iCloud request failed: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise ICloudError(
                "NEED_LOGIN",
                f"Could not reuse the session: {exc}. Run `icloud-docs-mcp login`.",
            ) from exc

        if getattr(api, "requires_2fa", False) or getattr(api, "requires_2sa", False):
            raise ICloudError(
                "NEED_2FA",
                "This Apple ID needs 2FA. Run `icloud-docs-mcp login` in a terminal. "
                "The MCP server will not wait for a code.",
            )

        self._api = api
        self._prepare_root()

    def _prepare_root(self) -> None:
        assert self._api is not None
        node = self._api.drive
        root_path = self.settings.root
        if root_path:
            try:
                node = self._walk_to(node, root_path)
            except ICloudError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise ICloudError(
                    "NOT_FOUND",
                    f"ICLOUD_ROOT '{root_path}' was not found: {exc}",
                ) from exc
        self._root_node = node

    def status(self) -> dict[str, object]:
        username = self.settings.require_username()
        payload: dict[str, object] = {
            "username": username,
            "session_dir": str(self.settings.session_dir),
            "download_dir": str(self.settings.download_dir),
            "root": self.settings.root or "",
            "authenticated": False,
            "trusted_session": False,
            "requires_2fa": False,
            "drive_reachable": False,
        }
        try:
            self.connect()
        except ICloudError as exc:
            payload["code"] = exc.code
            payload["error"] = exc.message
            return payload

        api = self._api
        payload["authenticated"] = True
        payload["trusted_session"] = bool(getattr(api, "is_trusted_session", False))
        payload["requires_2fa"] = bool(getattr(api, "requires_2fa", False))
        try:
            names = list(self._dir(self._require_root()))
            payload["drive_reachable"] = True
            payload["entry_count"] = len(names)
        except Exception as exc:  # noqa: BLE001
            payload["drive_reachable"] = False
            payload["error"] = str(exc)
            payload["code"] = "UNAVAILABLE"
        return payload

    def list_folder(self, path: str = "") -> list[DriveItem]:
        self.connect()
        rel = normalize_relpath(path)
        node = self._resolve(rel)
        node_type = _node_type(node)
        if node_type == "file":
            raise ICloudError("NOT_A_FOLDER", f"'{rel or '/'}' is a file, not a folder")
        items: list[DriveItem] = []
        for child in self._children(node):
            name = _node_name(child)
            child_path = join_relpath(rel, name)
            items.append(
                DriveItem(
                    path=child_path,
                    name=name,
                    type=_node_type(child),
                    size=_node_size(child),
                )
            )
        items.sort(key=lambda item: (item.type != "folder", item.name.lower()))
        return items

    def search(
        self,
        query: str = "",
        ext: str | None = None,
        path: str = "",
        limit: int = DEFAULT_SEARCH_LIMIT,
        max_visited: int = DEFAULT_MAX_VISITED,
        max_depth: int = DEFAULT_MAX_DEPTH,
    ) -> tuple[list[DriveItem], bool, int]:
        self.connect()
        if not query.strip() and not normalize_ext(ext):
            raise ICloudError(
                "INVALID_QUERY",
                "Provide a filename query and/or an extension filter.",
            )
        capped_limit = max(1, min(int(limit), MAX_SEARCH_LIMIT))
        start = normalize_relpath(path)
        matches: list[DriveItem] = []
        visited = 0
        truncated = False

        def walk(node: Any, rel: str, depth: int) -> None:
            nonlocal visited, truncated
            if len(matches) >= capped_limit:
                truncated = True
                return
            if depth > max_depth:
                truncated = True
                return
            children = self._children(node)
            for child in children:
                if len(matches) >= capped_limit:
                    truncated = True
                    return
                visited += 1
                if visited > max_visited:
                    truncated = True
                    return
                name = _node_name(child)
                child_path = join_relpath(rel, name)
                child_type = _node_type(child)
                if child_type == "file" and name_matches(name, child_path, query, ext):
                    matches.append(
                        DriveItem(
                            path=child_path,
                            name=name,
                            type="file",
                            size=_node_size(child),
                        )
                    )
                elif child_type in FOLDER_TYPES:
                    if name_matches(name, child_path, query, None) and not normalize_ext(
                        ext
                    ):
                        # Folder names can match a query when not filtering by file ext.
                        if query.strip() and query.lower() in name.lower():
                            matches.append(
                                DriveItem(
                                    path=child_path,
                                    name=name,
                                    type=child_type,
                                    size=None,
                                )
                            )
                    walk(child, child_path, depth + 1)

        walk(self._resolve(start), start, 0)
        return matches, truncated, visited

    def download(self, paths: Iterable[str]) -> list[dict[str, object]]:
        self.connect()
        results: list[dict[str, object]] = []
        for raw in paths:
            rel = normalize_relpath(raw)
            if not rel:
                results.append(
                    {
                        "path": raw,
                        "status": "error",
                        "error": "A file path is required",
                    }
                )
                continue
            try:
                dest = self._download_one(rel)
                results.append(
                    {
                        "path": rel,
                        "dest": str(dest),
                        "status": "downloaded",
                        "bytes": dest.stat().st_size,
                    }
                )
            except ICloudError as exc:
                results.append({"path": rel, "status": "error", "error": exc.message})
            except Exception as exc:  # noqa: BLE001
                results.append({"path": rel, "status": "error", "error": str(exc)})
        return results

    def read_text(self, path: str, limit: int | None = None) -> dict[str, object]:
        self.connect()
        rel = normalize_relpath(path)
        if not rel:
            raise ICloudError("INVALID_PATH", "A file path is required")
        dest = self._download_one(rel)
        extracted = extract_file(dest, limit=limit or 12_000)
        payload: dict[str, object] = {
            "path": rel,
            "local_path": str(dest),
            "content_type": extracted.content_type,
            "text": extracted.text,
            "truncated": extracted.truncated,
            "bytes": dest.stat().st_size,
        }
        if extracted.note:
            payload["note"] = extracted.note
        return payload

    def _download_one(self, rel: str) -> Path:
        node = self._resolve(rel)
        if _node_type(node) != "file":
            raise ICloudError("NOT_A_FILE", f"'{rel}' is not a file")
        dest = self.settings.download_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        size = _node_size(node)
        if dest.exists() and size is not None and dest.stat().st_size == size:
            return dest
        with node.open(stream=True) as response:
            with dest.open("wb") as handle:
                raw = getattr(response, "raw", None)
                if raw is not None:
                    copyfileobj(raw, handle)
                else:
                    handle.write(response.content)
        return dest

    def _require_root(self) -> Any:
        if self._root_node is None:
            raise ICloudError("UNAVAILABLE", "Drive client is not connected")
        return self._root_node

    def _resolve(self, rel: str) -> Any:
        node = self._require_root()
        if not rel:
            return node
        return self._walk_to(node, rel)

    def _walk_to(self, node: Any, rel: str) -> Any:
        current = node
        for part in rel.split("/"):
            try:
                current = current[part]
            except Exception as exc:  # noqa: BLE001
                raise ICloudError("NOT_FOUND", f"Path not found: {rel}") from exc
        return current

    def _children(self, node: Any) -> list[Any]:
        getter = getattr(node, "get_children", None)
        if callable(getter):
            try:
                return list(getter())
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("get_children failed: %s", exc)
                return []
        try:
            names = list(self._dir(node))
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("dir() failed: %s", exc)
            return []
        children = []
        for name in names:
            try:
                children.append(node[name])
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("child %s failed: %s", name, exc)
        return children

    @staticmethod
    def _dir(node: Any) -> list[str]:
        names = node.dir()
        return list(names) if names else []

    @staticmethod
    def _disable_keyring() -> None:
        # MCP is non-interactive. Never pop a system keyring prompt.
        os.environ.setdefault("PYTHON_KEYRING_BACKEND", "keyring.backends.null.Keyring")


def _node_name(node: Any) -> str:
    return str(getattr(node, "name", "") or "")


def _node_type(node: Any) -> str:
    return str(getattr(node, "type", "unknown") or "unknown").lower()


def _node_size(node: Any) -> int | None:
    size = getattr(node, "size", None)
    if size is None:
        return None
    try:
        return int(size)
    except (TypeError, ValueError):
        return None

