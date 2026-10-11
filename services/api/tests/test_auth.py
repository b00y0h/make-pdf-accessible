import logging
from unittest.mock import Mock, patch

import pytest
from app.auth import BetterAuthSessionValidator, User, get_dashboard_user
from app.config import settings
from app.models import UserRole
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

DASHBOARD_SECRET = "test-dashboard-secret-0123456789abcdef"
OLD_LITERAL_SECRET = "dashboard_internal_secret_123"


class TestUser:
    """Test User model"""

    def test_user_creation(self):
        """Test user creation with basic info"""
        user = User(
            sub="user-123",
            name="Test User",
            email="test@example.com",
            role="admin",
            org_id="org-1",
        )

        assert user.sub == "user-123"
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert user.role == "admin"
        assert user.org_id == "org-1"

    def test_user_default_role(self):
        """Test users default to the viewer role"""
        user = User(sub="user-123")

        assert user.role == UserRole.VIEWER.value

    def test_user_has_role(self):
        """Test role checking"""
        user = User(sub="user-123", role="viewer")

        assert user.has_role(UserRole.VIEWER)
        assert not user.has_role(UserRole.ADMIN)

    def test_user_is_admin(self):
        """Test admin role checking"""
        admin_user = User(sub="admin-123", role="admin")
        viewer_user = User(sub="viewer-123", role="viewer")

        assert admin_user.is_admin()
        assert not viewer_user.is_admin()

    def test_user_can_access_resource(self):
        """Test resource access permissions"""
        user = User(sub="user-123", role="viewer")
        admin = User(sub="admin-123", role="admin")

        # User can access their own resources
        assert user.can_access_resource("user-123")

        # User cannot access other user's resources
        assert not user.can_access_resource("other-user")

        # Admin can access any resource
        assert admin.can_access_resource("any-user")


@pytest.fixture
def dashboard_secret(monkeypatch):
    """Configure the internal dashboard secret for a test"""
    monkeypatch.setattr(settings, "dashboard_internal_secret", DASHBOARD_SECRET)
    return DASHBOARD_SECRET


@pytest.fixture
def no_dashboard_secret(monkeypatch):
    """Leave the internal dashboard secret unset for a test"""
    monkeypatch.setattr(settings, "dashboard_internal_secret", None)


async def assert_dashboard_rejected(internal, secret):
    with pytest.raises(HTTPException) as exc_info:
        await get_dashboard_user(
            x_dashboard_internal=internal, x_dashboard_secret=secret
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Dashboard authentication required"


class TestGetDashboardUser:
    """Test the internal dashboard authentication dependency"""

    @pytest.mark.asyncio
    async def test_accepts_configured_secret(self, dashboard_secret):
        user = await get_dashboard_user(
            x_dashboard_internal="true", x_dashboard_secret=dashboard_secret
        )

        assert user.sub == "dashboard_system_user"
        assert user.is_admin()
        assert user.org_id == "system"

    @pytest.mark.asyncio
    async def test_rejects_missing_secret(self, dashboard_secret):
        await assert_dashboard_rejected("true", None)

    @pytest.mark.asyncio
    async def test_rejects_empty_secret(self, dashboard_secret):
        await assert_dashboard_rejected("true", "")

    @pytest.mark.asyncio
    async def test_rejects_wrong_secret(self, dashboard_secret):
        await assert_dashboard_rejected("true", "wrong-secret")

    @pytest.mark.asyncio
    async def test_rejects_secret_prefix(self, dashboard_secret):
        await assert_dashboard_rejected("true", dashboard_secret[:-1])

    @pytest.mark.asyncio
    async def test_rejects_old_hardcoded_secret(self, dashboard_secret):
        await assert_dashboard_rejected("true", OLD_LITERAL_SECRET)

    @pytest.mark.asyncio
    async def test_rejects_non_ascii_secret(self, dashboard_secret):
        await assert_dashboard_rejected("true", "sécret")

    @pytest.mark.asyncio
    async def test_rejects_missing_internal_header(self, dashboard_secret):
        await assert_dashboard_rejected(None, dashboard_secret)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "secret", [None, "", "anything", OLD_LITERAL_SECRET, DASHBOARD_SECRET]
    )
    async def test_rejects_everything_when_secret_unset(
        self, no_dashboard_secret, secret
    ):
        await assert_dashboard_rejected("true", secret)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("secret", [None, "", "anything"])
    async def test_rejects_everything_when_secret_empty(self, monkeypatch, secret):
        monkeypatch.setattr(settings, "dashboard_internal_secret", "")

        await assert_dashboard_rejected("true", secret)


class TestGetDashboardUserHeaders:
    """Test the dependency reads the X-Dashboard-* request headers"""

    @pytest.fixture
    def client(self):
        app = FastAPI()

        @app.get("/protected")
        async def protected(user: User = Depends(get_dashboard_user)):
            return {"sub": user.sub, "role": user.role}

        return TestClient(app)

    def test_accepts_configured_secret_header(self, client, dashboard_secret):
        response = client.get(
            "/protected",
            headers={
                "X-Dashboard-Internal": "true",
                "X-Dashboard-Secret": dashboard_secret,
            },
        )

        assert response.status_code == 200
        assert response.json() == {"sub": "dashboard_system_user", "role": "admin"}

    @pytest.mark.parametrize(
        "headers",
        [
            {},
            {"X-Dashboard-Internal": "true"},
            {"X-Dashboard-Internal": "true", "X-Dashboard-Secret": "wrong-secret"},
            {"X-Dashboard-Internal": "true", "X-Dashboard-Secret": OLD_LITERAL_SECRET},
        ],
    )
    def test_rejects_bad_headers(self, client, dashboard_secret, headers):
        response = client.get("/protected", headers=headers)

        assert response.status_code == 403

    def test_rejects_when_secret_unset(self, client, no_dashboard_secret):
        response = client.get(
            "/protected",
            headers={
                "X-Dashboard-Internal": "true",
                "X-Dashboard-Secret": OLD_LITERAL_SECRET,
            },
        )

        assert response.status_code == 403


class TestSessionValidatorLogging:
    """Test session validation never writes tokens or user data to logs"""

    SESSION_TOKEN = "session-token-abc123"
    COOKIE_NAME = "better-auth.session_token"
    USER_EMAIL = "person@example.com"

    def validate(self, response):
        validator = BetterAuthSessionValidator("http://auth.test")
        request = Mock(cookies={self.COOKIE_NAME: self.SESSION_TOKEN})

        with patch("app.auth.requests.get", return_value=response) as mock_get:
            result = validator.validate_session(request)

        mock_get.assert_called_once()
        return result

    def assert_nothing_sensitive(self, caplog, capsys):
        output = caplog.text + capsys.readouterr().out
        for sensitive in (self.SESSION_TOKEN, self.COOKIE_NAME, self.USER_EMAIL):
            assert sensitive not in output

    def test_valid_session_logs_nothing_sensitive(self, caplog, capsys):
        session_data = {
            "session": {"token": self.SESSION_TOKEN},
            "user": {"id": "user-1", "email": self.USER_EMAIL},
        }
        response = Mock(status_code=200, text=str(session_data))
        response.json.return_value = session_data

        with caplog.at_level(logging.DEBUG, logger="app.auth"):
            result = self.validate(response)

        assert result == session_data
        assert caplog.records, "expected debug logging from the validator"
        assert all(r.levelno == logging.DEBUG for r in caplog.records)
        self.assert_nothing_sensitive(caplog, capsys)

    def test_error_response_body_is_not_logged(self, caplog, capsys):
        response = Mock(
            status_code=401,
            text=f"invalid token {self.SESSION_TOKEN} for {self.USER_EMAIL}",
        )

        with caplog.at_level(logging.DEBUG, logger="app.auth"):
            assert self.validate(response) is None

        self.assert_nothing_sensitive(caplog, capsys)

    def test_unparseable_body_is_not_logged(self, caplog, capsys):
        response = Mock(status_code=200, text=f"not json {self.SESSION_TOKEN}")
        response.json.side_effect = ValueError(f"bad json {self.SESSION_TOKEN}")

        with caplog.at_level(logging.DEBUG, logger="app.auth"):
            assert self.validate(response) is None

        self.assert_nothing_sensitive(caplog, capsys)

    def test_exception_message_is_not_logged(self, caplog, capsys):
        validator = BetterAuthSessionValidator("http://auth.test")
        request = Mock(cookies={self.COOKIE_NAME: self.SESSION_TOKEN})

        with (
            caplog.at_level(logging.DEBUG, logger="app.auth"),
            patch(
                "app.auth.requests.get",
                side_effect=RuntimeError(f"failed with {self.SESSION_TOKEN}"),
            ),
        ):
            assert validator.validate_session(request) is None

        self.assert_nothing_sensitive(caplog, capsys)
