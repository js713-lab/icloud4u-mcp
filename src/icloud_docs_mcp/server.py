"""stdio MCP server. Logs go to stderr; stdout is JSON-RPC only."""

from __future__ import annotations

import logging
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP as MCPServer
except ImportError:  # mcp 2.x
    from mcp.server import MCPServer

from icloud_docs_mcp.client import DriveClient
from icloud_docs_mcp.config import Settings, load_settings
from icloud_docs_mcp.errors import ICloudError, ok

LOGGER = logging.getLogger(__name__)

mcp = MCPServer(
    "icloud-docs",
    instructions=(
        "Read-only access to the user's iCloud Drive. Use status first if a tool "
        "returns NEED_LOGIN or NEED_2FA — the user must run `icloud-docs-mcp login` "
        "in a terminal. Prefer search over recursive listing. Do not request a "
        "password or 2FA code through these tools."
    ),
)

_settings: Settings | None = None
_client: DriveClient | None = None


def configure(
    settings: Settings | None = None, client: DriveClient | None = None
) -> None:
    global _settings, _client
    _settings = settings or load_settings()
    _client = client


def get_client() -> DriveClient:
    global _client
    if _client is None:
        settings = _settings or load_settings()
        _client = DriveClient(settings)
    return _client


def _call(fn, *args: Any, **kwargs: Any) -> dict[str, Any]:
    try:
        return fn(*args, **kwargs)
    except ICloudError as exc:
        if exc.code in {"NEED_LOGIN", "NEED_2FA"}:
            _reset_client()
        return exc.to_dict()
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("unexpected iCloud tool error")
        return {
            "ok": False,
            "code": "UNAVAILABLE",
            "error": f"{type(exc).__name__}: {exc}",
        }


def _reset_client() -> None:
    global _client
    _client = None


@mcp.tool()
def status() -> dict[str, Any]:
    """Check whether the Apple ID session is trusted and iCloud Drive is reachable."""

    def _run() -> dict[str, Any]:
        payload = get_client().status()
        if payload.get("drive_reachable"):
            return ok(**payload)
        return {"ok": False, **payload}

    return _call(_run)


@mcp.tool()
def list_folder(path: str = "") -> dict[str, Any]:
    """List one iCloud Drive folder (not recursive). Empty path is the configured root."""

    def _run() -> dict[str, Any]:
        items = get_client().list_folder(path)
        return ok(path=path, count=len(items), items=[item.to_dict() for item in items])

    return _call(_run)


@mcp.tool()
def search(
    query: str = "",
    ext: str = "",
    path: str = "",
    limit: int = 30,
) -> dict[str, Any]:
    """Search Drive filenames and paths. Optional ext filter like pdf or .docx. Capped."""

    def _run() -> dict[str, Any]:
        items, truncated, visited = get_client().search(
            query=query,
            ext=ext or None,
            path=path,
            limit=limit,
        )
        return ok(
            query=query,
            ext=ext or None,
            path=path or "",
            count=len(items),
            truncated=truncated,
            visited=visited,
            items=[item.to_dict() for item in items],
        )

    return _call(_run)


@mcp.tool()
def download(paths: list[str]) -> dict[str, Any]:
    """Download Drive files to the local cache directory. Returns local paths, not bytes."""

    def _run() -> dict[str, Any]:
        if not paths:
            raise ICloudError("INVALID_PATH", "Provide one or more Drive paths")
        results = get_client().download(paths)
        errors = [row for row in results if row.get("status") == "error"]
        return ok(
            count=len(results),
            error_count=len(errors),
            results=results,
        )

    return _call(_run)


@mcp.tool()
def read_text(path: str) -> dict[str, Any]:
    """Download a Drive file if needed and return extracted text (pdf, docx, xlsx, txt)."""

    def _run() -> dict[str, Any]:
        payload = get_client().read_text(path)
        return ok(**payload)

    return _call(_run)


def run() -> None:
    configure()
    mcp.run(transport="stdio")
