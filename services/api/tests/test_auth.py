from unittest.mock import Mock, patch

import pytest
import requests
from app.auth import (
    BetterAuthSessionValidator,
    User,
    get_admin_user,
    get_current_user,
    require_roles,
)
from app.models import UserRole
from fastapi import HTTPException


def make_request(cookies=None):
    """Build a stand-in for the incoming FastAPI request."""
    request = Mock()
    request.cookies = cookies or {}
    return request


def make_response(status_code=200, text="", json_data=None):
    """Build a stand-in for the BetterAuth session response."""
    response = Mock()
    response.status_code = status_code
    response.text = text
    response.json.return_value = json_data
    return response


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
            token_claims={"id": "user-123"},
        )

        assert user.sub == "user-123"
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert user.role == "admin"
        assert user.org_id == "org-1"
        assert user.token_claims == {"id": "user-123"}

    def test_user_defaults(self):
        """Test defaults for optional fields"""
        user = User(sub="user-123")

        assert user.name == ""
        assert user.email is None
        assert user.role == UserRole.VIEWER.value
        assert user.org_id is None
        assert user.token_claims == {}

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


class TestBetterAuthSessionValidator:
    """Test session validation against BetterAuth"""

    def setup_method(self):
        self.validator = BetterAuthSessionValidator("https://auth.example.com/")

    def test_strips_trailing_slash(self):
        """Test the base URL is normalized"""
        assert self.validator.better_auth_url == "https://auth.example.com"

    def test_no_cookies(self):
        """Test requests without cookies are not sent to BetterAuth"""
        with patch("app.auth.requests.get") as mock_get:
            assert self.validator.validate_session(make_request()) is None
            mock_get.assert_not_called()

    def test_valid_session(self):
        """Test a valid session is returned and cookies are forwarded"""
        session = {"session": {"id": "s-1"}, "user": {"id": "user-123"}}
        cookies = {"better-auth.session_token": "token"}

        with patch("app.auth.requests.get") as mock_get:
            mock_get.return_value = make_response(
                text='{"session": {}, "user": {}}', json_data=session
            )

            assert self.validator.validate_session(make_request(cookies)) == session
            mock_get.assert_called_once_with(
                "https://auth.example.com/api/auth/get-session",
                cookies=cookies,
                timeout=5.0,
            )

    @pytest.mark.parametrize(
        "response",
        [
            make_response(status_code=401, text="Unauthorized"),
            make_response(text="null"),
            make_response(text=""),
            make_response(text='{"session": {}}', json_data={"session": {}}),
            make_response(text="[]", json_data=[]),
        ],
        ids=["non-200", "null", "empty", "no-user", "not-a-dict"],
    )
    def test_invalid_session(self, response):
        """Test responses without a usable session are rejected"""
        with patch("app.auth.requests.get", return_value=response):
            assert (
                self.validator.validate_session(make_request({"session": "token"}))
                is None
            )

    def test_unparseable_response(self):
        """Test a response that is not JSON is rejected"""
        response = make_response(text="<html>")
        response.json.side_effect = ValueError("not JSON")

        with patch("app.auth.requests.get", return_value=response):
            assert (
                self.validator.validate_session(make_request({"session": "token"}))
                is None
            )

    def test_request_error(self):
        """Test network errors are treated as no session"""
        with patch(
            "app.auth.requests.get",
            side_effect=requests.ConnectionError("unreachable"),
        ):
            assert (
                self.validator.validate_session(make_request({"session": "token"}))
                is None
            )


class TestGetCurrentUser:
    """Test get_current_user dependency"""

    @pytest.mark.asyncio
    async def test_extract_user_from_session(self):
        """Test building the user from BetterAuth session data"""
        session = {
            "user": {
                "id": "user-123",
                "name": "Test User",
                "email": "test@example.com",
                "role": "admin",
                "orgId": "org-1",
            }
        }

        with patch("app.auth.session_validator.validate_session", return_value=session):
            user = await get_current_user(make_request())

        assert user.sub == "user-123"
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert user.role == "admin"
        assert user.org_id == "org-1"
        assert user.token_claims == session["user"]

    @pytest.mark.asyncio
    async def test_extract_user_default_role(self):
        """Test default role assignment"""
        with patch(
            "app.auth.session_validator.validate_session",
            return_value={"user": {"id": "user-123"}},
        ):
            user = await get_current_user(make_request())

        assert user.role == UserRole.VIEWER.value

    @pytest.mark.asyncio
    async def test_no_session(self):
        """Test requests without a session are rejected"""
        with patch("app.auth.session_validator.validate_session", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(make_request())

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Not authenticated"


class TestRoleChecks:
    """Test admin and role-based dependencies"""

    @pytest.mark.asyncio
    async def test_admin_user_allowed(self):
        """Test admins pass the admin check"""
        with patch(
            "app.auth.session_validator.validate_session",
            return_value={"user": {"id": "admin-123", "role": "admin"}},
        ):
            user = await get_admin_user(make_request())

        assert user.sub == "admin-123"

    @pytest.mark.asyncio
    async def test_viewer_rejected_by_admin_check(self):
        """Test viewers fail the admin check"""
        with patch(
            "app.auth.session_validator.validate_session",
            return_value={"user": {"id": "user-123", "role": "viewer"}},
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_admin_user(make_request())

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Admin role required"

    def test_require_roles(self):
        """Test the role checker allows listed roles and rejects others"""
        checker = require_roles([UserRole.ADMIN])
        admin = User(sub="admin-123", role="admin")
        viewer = User(sub="user-123", role="viewer")

        assert checker(current_user=admin) is admin

        with pytest.raises(HTTPException) as exc_info:
            checker(current_user=viewer)

        assert exc_info.value.status_code == 403
