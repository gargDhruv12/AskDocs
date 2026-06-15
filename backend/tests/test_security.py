import pytest
from fastapi import HTTPException
from app.security import safe_display_name, sign_page, verify_page_signature, workspace_id


def test_workspace_id_rejects_untrusted_values():
    with pytest.raises(HTTPException):
        workspace_id("../../other-user")


def test_display_name_removes_paths():
    assert safe_display_name("../../private/report.pdf") == "report.pdf"


def test_page_signatures_are_scoped_to_document_and_page():
    expires, signature = sign_page("team", "doc-1", 3, "secret")
    verify_page_signature("team", "doc-1", 3, expires, signature, "secret")
    with pytest.raises(HTTPException):
        verify_page_signature("team", "doc-1", 4, expires, signature, "secret")
