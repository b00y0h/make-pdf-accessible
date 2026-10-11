"""API tests for the alt-text review endpoints"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from app.auth import User, get_current_user
from app.main import app
from fastapi.testclient import TestClient

DOC_ID = "12345678-1234-1234-1234-123456789012"
OWNER = User(sub="owner-123", name="Owner", role="viewer")
OTHER_USER = User(sub="other-456", name="Other", role="viewer")
ADMIN = User(sub="admin-789", name="Admin", role="admin")

# The dashboard calls the unprefixed paths; integrators use /v1
PREFIXES = ["", "/v1"]


def _version(version: int, text: str, editor_id: str = "system") -> dict:
    """A stored alt-text version"""
    return {
        "version": version,
        "text": text,
        "editor_id": editor_id,
        "editor_name": editor_id,
        "timestamp": datetime(2026, 10, 1, 12, version),
        "comment": None,
        "is_ai_generated": editor_id == "system",
        "confidence": 0.9 if editor_id == "system" else None,
    }


def _alt_text_doc(chart_versions=None, chart_status="needs_review") -> dict:
    """A stored alt-text document with a chart and a logo figure"""
    chart_versions = chart_versions or [_version(1, "A bar chart")]
    return {
        "docId": DOC_ID,
        "figures": [
            {
                "figure_id": "fig-chart",
                "status": chart_status,
                "current_version": chart_versions[-1]["version"],
                "ai_text": "A bar chart",
                "approved_text": None,
                "confidence": 0.9,
                "generation_method": "bedrock_vision",
                "versions": chart_versions,
                "context": {"page": 1},
                "bounding_box": {"left": 0.1, "top": 0.2, "width": 0.5, "height": 0.4},
                "page_number": 1,
            },
            {
                "figure_id": "fig-logo",
                "status": "approved",
                "current_version": 1,
                "ai_text": "Company logo",
                "approved_text": "Company logo",
                "versions": [_version(1, "Company logo")],
            },
        ],
        "total_figures": 2,
        "pending_review": 1,
        "approved": 1,
        "edited": 0,
        "updated_at": datetime(2026, 10, 1, 12, 30),
    }


@pytest.fixture
def client():
    """Test client that signs the user out afterwards"""
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def repos():
    """Mocked alt-text and document repositories; OWNER owns DOC_ID"""
    alt_text_repo = Mock()
    alt_text_repo.get_document_alt_text.return_value = _alt_text_doc()
    doc_repo = Mock()
    doc_repo.get_document.return_value = {"docId": DOC_ID, "ownerId": OWNER.sub}

    with (
        patch(
            "app.services.alt_text.get_alt_text_repository",
            return_value=alt_text_repo,
        ),
        patch("app.services.alt_text.get_document_repository", return_value=doc_repo),
    ):
        yield alt_text_repo, doc_repo


def sign_in(user: User) -> None:
    """Authenticate requests as the given user"""
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.mark.parametrize("prefix", PREFIXES)
def test_owner_gets_alt_text(client, repos, prefix):
    """The document owner reads every figure with its versions"""
    sign_in(OWNER)

    response = client.get(f"{prefix}/documents/{DOC_ID}/alt-text")

    assert response.status_code == 200
    data = response.json()
    assert data["doc_id"] == DOC_ID
    assert [figure["figure_id"] for figure in data["figures"]] == [
        "fig-chart",
        "fig-logo",
    ]
    assert data["pending_review"] == 1
    assert data["figures"][0]["versions"][0]["timestamp"] == "2026-10-01T12:01:00"


def test_status_filter_narrows_figures(client, repos):
    """The status filter returns only figures in that status"""
    sign_in(OWNER)

    response = client.get(
        f"/documents/{DOC_ID}/alt-text", params={"status_filter": "approved"}
    )

    assert response.status_code == 200
    assert [figure["figure_id"] for figure in response.json()["figures"]] == [
        "fig-logo"
    ]


def test_non_owner_cannot_get_alt_text(client, repos):
    """Another user gets 404 and the alt text is never read"""
    alt_text_repo, _ = repos
    sign_in(OTHER_USER)

    response = client.get(f"/documents/{DOC_ID}/alt-text")

    assert response.status_code == 404
    assert response.json()["message"] == "Alt text data not found or access denied"
    alt_text_repo.get_document_alt_text.assert_not_called()


def test_admin_gets_any_document_alt_text(client, repos):
    """Admins read alt text without an ownership check"""
    _, doc_repo = repos
    sign_in(ADMIN)

    response = client.get(f"/documents/{DOC_ID}/alt-text")

    assert response.status_code == 200
    doc_repo.get_document.assert_not_called()


def test_alt_text_requires_session(client, repos):
    """Requests without a session are rejected"""
    response = client.get(f"/documents/{DOC_ID}/alt-text")

    assert response.status_code == 403
    assert response.json()["message"] == "Not authenticated"


@pytest.mark.parametrize("prefix", PREFIXES)
def test_owner_edits_alt_text(client, repos, prefix):
    """An edit creates a new version attributed to the editor"""
    alt_text_repo, _ = repos
    alt_text_repo.edit_figure_alt_text.return_value = True
    alt_text_repo.get_document_alt_text.return_value = _alt_text_doc(
        chart_versions=[
            _version(1, "A bar chart"),
            _version(2, "Revenue by quarter", editor_id=OWNER.sub),
        ],
        chart_status="edited",
    )
    sign_in(OWNER)

    response = client.patch(
        f"{prefix}/documents/{DOC_ID}/alt-text",
        json={
            "figure_id": "fig-chart",
            "text": "  Revenue by quarter  ",
            "comment": "More specific",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["version"] == 2
    assert data["text"] == "Revenue by quarter"
    assert data["status"] == "edited"
    alt_text_repo.edit_figure_alt_text.assert_called_once_with(
        doc_id=DOC_ID,
        figure_id="fig-chart",
        new_text="Revenue by quarter",
        editor_id=OWNER.sub,
        editor_name="Owner",
        comment="More specific",
    )


def test_non_owner_cannot_edit_alt_text(client, repos):
    """Another user gets 403 and nothing is written"""
    alt_text_repo, _ = repos
    sign_in(OTHER_USER)

    response = client.patch(
        f"/documents/{DOC_ID}/alt-text",
        json={"figure_id": "fig-chart", "text": "Vandalised"},
    )

    assert response.status_code == 403
    alt_text_repo.edit_figure_alt_text.assert_not_called()


def test_owner_updates_figure_status(client, repos):
    """Approving figures updates their status"""
    alt_text_repo, _ = repos
    alt_text_repo.bulk_update_status.return_value = 1
    sign_in(OWNER)

    response = client.patch(
        f"/documents/{DOC_ID}/alt-text/status",
        json={"figure_ids": ["fig-chart"], "status": "approved"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["updated_count"] == 1
    assert data["status"] == "approved"
    assert alt_text_repo.bulk_update_status.call_args.kwargs["status"] == "approved"


def test_owner_gets_figure_history(client, repos):
    """The history lists every version of a figure"""
    alt_text_repo, _ = repos
    alt_text_repo.get_figure_history.return_value = {
        "figure_id": "fig-chart",
        "versions": [
            _version(1, "A bar chart"),
            _version(2, "Revenue by quarter", editor_id=OWNER.sub),
        ],
        "current_version": 2,
        "status": "edited",
    }
    sign_in(OWNER)

    response = client.get(f"/documents/{DOC_ID}/alt-text/fig-chart/history")

    assert response.status_code == 200
    data = response.json()
    assert [version["version"] for version in data["versions"]] == [1, 2]
    assert data["current_version"] == 2


def test_owner_reverts_to_version(client, repos):
    """A revert adds a new version with the old text"""
    alt_text_repo, _ = repos
    alt_text_repo.revert_to_version.return_value = True
    alt_text_repo.get_document_alt_text.return_value = _alt_text_doc(
        chart_versions=[
            _version(1, "A bar chart"),
            _version(2, "Revenue by quarter", editor_id=OWNER.sub),
            _version(3, "A bar chart", editor_id=OWNER.sub),
        ],
        chart_status="edited",
    )
    sign_in(OWNER)

    response = client.post(f"/documents/{DOC_ID}/alt-text/fig-chart/revert/1")

    assert response.status_code == 200
    data = response.json()
    assert data["version"] == 3
    assert data["text"] == "A bar chart"
    assert alt_text_repo.revert_to_version.call_args.kwargs["version"] == 1


def test_review_dashboard_requires_admin(client, repos):
    """Viewers cannot read the review dashboard"""
    sign_in(OWNER)

    response = client.get("/documents/alt-text/dashboard")

    assert response.status_code == 403


@pytest.mark.parametrize("prefix", PREFIXES)
def test_admin_gets_review_dashboard(client, repos, prefix):
    """Admins get review totals across documents"""
    alt_text_repo, _ = repos
    alt_text_repo.get_documents_needing_review.return_value = [
        {
            "_id": "65f0c0ffee0000000000abcd",
            "docId": DOC_ID,
            "total_figures": 2,
            "pending_review": 1,
            "approved": 1,
            "edited": 0,
            "updated_at": datetime(2026, 10, 1, 12, 30),
        }
    ]
    sign_in(ADMIN)

    response = client.get(f"{prefix}/documents/alt-text/dashboard")

    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary["total_figures"] == 2
    assert summary["pending_review"] == 1
    assert summary["completion_rate"] == 50.0
