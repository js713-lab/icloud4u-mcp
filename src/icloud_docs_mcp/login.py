"""Interactive Apple ID login for a real terminal. Not used by the MCP server."""

from __future__ import annotations

import getpass
import os
import sys
from typing import TextIO

from icloud_docs_mcp.config import Settings
from icloud_docs_mcp.errors import ICloudError


def login(
    settings: Settings,
    *,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Authenticate, complete 2FA if needed, and persist a trusted cookiejar."""
    os.environ.setdefault("PYTHON_KEYRING_BACKEND", "keyring.backends.null.Keyring")

    username = settings.username
    if not username:
        stdout.write("Apple ID: ")
        stdout.flush()
        username = stdin.readline().strip()
    if not username:
        stderr.write("An Apple ID is required.\n")
        return 1

    password = settings.password
    if not password:
        password = getpass.getpass(f"Password for {username}: ")
    if not password:
        stderr.write("A password is required.\n")
        return 1

    settings.session_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(settings.session_dir, 0o700)
    except OSError:
        stderr.write("Warning: could not restrict session directory permissions.\n")

    from pyicloud import PyiCloudService
    from pyicloud.exceptions import (
        PyiCloudFailedLoginException,
        PyiCloudTrustedDevicePromptException,
    )

    try:
        api = PyiCloudService(
            username,
            password,
            cookie_directory=str(settings.session_dir),
            accept_terms=True,
        )
    except PyiCloudFailedLoginException as exc:
        stderr.write(f"Login failed: {exc}\n")
        return 1

    if getattr(api, "requires_2fa", False):
        if getattr(api, "security_key_names", None):
            stderr.write(
                "This Apple ID wants a hardware security key, which this CLI does not support.\n"
            )
            return 1
        stdout.write("Two-factor authentication is required.\n")
        sent = False
        try:
            sent = bool(api.request_2fa_code())
        except PyiCloudTrustedDevicePromptException as exc:
            stderr.write(f"Could not start the trusted-device prompt: {exc}\n")
        except Exception as exc:  # noqa: BLE001
            stderr.write(f"Could not request a 2FA code: {type(exc).__name__}: {exc}\n")
        method = getattr(api, "two_factor_delivery_method", "unknown")
        notice = getattr(api, "two_factor_delivery_notice", None)
        if notice:
            stdout.write(f"{notice}\n")
        stdout.write(f"2FA method: {method} (requested={sent})\n")
        stdout.write("Enter the 6-digit code from your Apple device.\n")
        for attempt in range(3):
            stdout.write("2FA code: ")
            stdout.flush()
            code = stdin.readline().strip().replace(" ", "")
            if not code:
                stdout.write("Empty code. Try again.\n")
                continue
            try:
                accepted = bool(api.validate_2fa_code(code))
            except Exception as exc:  # noqa: BLE001
                accepted = False
                stdout.write(f"Rejected ({type(exc).__name__}: {exc}).\n")
            if accepted:
                stdout.write("2FA accepted.\n")
                break
            left = 2 - attempt
            if left <= 0:
                stderr.write("2FA failed. Wait a few minutes, then try again.\n")
                return 1
            stdout.write(f"Rejected. {left} attempt(s) left.\n")
        else:
            return 1

    if getattr(api, "requires_2sa", False):
        stderr.write(
            "Two-step authentication (older Apple IDs) is not supported. Use 2FA.\n"
        )
        return 1

    if not getattr(api, "is_trusted_session", False):
        trusted = api.trust_session()
        stdout.write(f"Session trust: {trusted}\n")

    stdout.write(f"Logged in. Session saved under {settings.session_dir}\n")
    return 0


def print_status(settings: Settings, stdout: TextIO = sys.stdout) -> int:
    from icloud_docs_mcp.client import DriveClient
    from icloud_docs_mcp.errors import ok

    client = DriveClient(settings)
    try:
        payload = client.status()
        if payload.get("drive_reachable"):
            stdout.write(_json(ok(**payload)) + "\n")
            return 0
        stdout.write(_json(payload) + "\n")
        return 1 if payload.get("code") else 0
    except ICloudError as exc:
        stdout.write(_json(exc.to_dict()) + "\n")
        return 1


def _json(payload: dict) -> str:
    import json

    return json.dumps(payload, indent=2)
