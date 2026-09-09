"""Structured errors returned by tools and the CLI."""

from __future__ import annotations


class ICloudError(Exception):
    """Recoverable iCloud or config failure with a stable machine code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, object]:
        return {"ok": False, "error": self.message, "code": self.code}


def ok(**payload: object) -> dict[str, object]:
    return {"ok": True, **payload}
