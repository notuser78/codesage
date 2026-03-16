"""Unit tests for authentication utilities."""

from types import SimpleNamespace

import pytest

from middleware.auth import PermissionChecker, create_access_token, verify_token


def test_jwt_token_roundtrip():
    token = create_access_token("user-123", "user@example.com", roles=["user"])
    payload = verify_token(token)

    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["email"] == "user@example.com"
    assert "user" in payload.get("roles", [])


def test_permission_checker_allows_user_role():
    token = create_access_token("user-123", "user@example.com", roles=["user"])
    payload = verify_token(token)

    request = SimpleNamespace(state=SimpleNamespace(user=payload))
    checker = PermissionChecker(["user"])

    assert checker(request) == payload


def test_permission_checker_denies_missing_role():
    token = create_access_token("user-123", "user@example.com", roles=["guest"])
    payload = verify_token(token)

    request = SimpleNamespace(state=SimpleNamespace(user=payload))
    checker = PermissionChecker(["user"])

    with pytest.raises(Exception):
        checker(request)
