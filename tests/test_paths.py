from icloud_docs_mcp.errors import ICloudError
from icloud_docs_mcp.paths import (
    join_relpath,
    name_matches,
    normalize_ext,
    normalize_relpath,
    sanitize_username,
)
import pytest


def test_normalize_relpath_strips_slashes():
    assert normalize_relpath("/Documents/Work/") == "Documents/Work"
    assert normalize_relpath("") == ""
    assert normalize_relpath(".") == ""


def test_normalize_relpath_rejects_parent_segments():
    with pytest.raises(ICloudError) as exc:
        normalize_relpath("Documents/../Secrets")
    assert exc.value.code == "INVALID_PATH"


def test_join_relpath():
    assert join_relpath("Documents", "Work", "file.pdf") == "Documents/Work/file.pdf"
    assert join_relpath("", "a") == "a"


def test_sanitize_username_is_filesystem_safe():
    assert sanitize_username("You.Name+tag@example.com") == "younametagexamplecom"


def test_name_matches_query_and_ext():
    assert name_matches("Budget 2024.pdf", "Finance", "budget", ".pdf")
    assert not name_matches("Budget 2024.pdf", "Finance", "budget", ".docx")
    assert name_matches("notes.txt", "", "", "txt")
    assert not name_matches("notes.txt", "", "invoice", None)


def test_normalize_ext():
    assert normalize_ext("PDF") == ".pdf"
    assert normalize_ext(".Docx") == ".docx"
    assert normalize_ext("") is None
