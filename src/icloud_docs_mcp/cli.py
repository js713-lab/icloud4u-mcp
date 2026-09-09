"""Command-line entry: login, status, or stdio MCP server (default)."""

from __future__ import annotations

import argparse
import logging
import sys

from icloud_docs_mcp.config import load_dotenv, load_settings


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s %(levelname)s: %(message)s",
        stream=sys.stderr,
    )
    logging.getLogger("pyicloud").setLevel(logging.WARNING)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="icloud-docs-mcp",
        description="Read-only iCloud Drive MCP server and login helper.",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("login", help="Interactive Apple ID + 2FA login (TTY required)")
    sub.add_parser("status", help="Show session health as JSON")
    sub.add_parser("serve", help="Run the stdio MCP server (default)")
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_logging()
    load_dotenv()
    args = build_parser().parse_args(argv)
    settings = load_settings()

    if args.command == "login":
        from icloud_docs_mcp.login import login

        return login(settings)
    if args.command == "status":
        from icloud_docs_mcp.login import print_status

        return print_status(settings)

    # Default: MCP stdio. Do not print a banner; stdout is the protocol.
    from icloud_docs_mcp.server import run

    run()
    return 0
