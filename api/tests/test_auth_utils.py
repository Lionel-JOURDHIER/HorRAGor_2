
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from api.auth_utils import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    get_current_user,
    hash_password,
    revoke_all_user_tokens,
    revoke_refresh_token,
    validate_refresh_token,
    verify_password,
)
from fastapi import HTTPException

# ============================================================================
# PASSWORD HASHING
# ============================================================================


def test_hash_password():
    password = "password123"

    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$2")


def test_verify_password_success():
    password = "password123"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_failure():
    password = "password123"
    hashed = hash_password(password)

    assert verify_password("wrong_password", hashed) is False


# ============================================================================
# ACCESS TOKEN
# ============================================================================


def test_create_access_token():
    data = {
        "sub": "1",
        "email": "test@example.com",
    }

    token = create_access_token(data)

    assert isinstance(token, str)
    assert len(token) > 0

    payload = decode_access_token(token)

    assert payload["sub"] == "1"
    assert payload["email"] == "test@example.com"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_create_access_token_custom_expiration():
    data = {"sub": "1"}
    expires_delta = timedelta(minutes=5)

    token = create_access_token(
        data,
        expires_delta=expires_delta,
    )

    payload = decode_access_token(token)

    assert payload["sub"] == "1"
    assert payload["type"] == "access"


def test_decode_access_token_invalid():
    with pytest.raises(HTTPException) as exc:
        decode_access_token("invalid.token")

    assert exc.value.status_code == 401
    assert exc.value.detail == "Token invalide ou expiré"
    assert exc.value.headers == {"WWW-Authenticate": "Bearer"}


def test_decode_access_token_wrong_type():
    with patch(
        "api.auth_utils.jwt.decode",
        return_value={
            "sub": "1",
            "type": "refresh",
        },
    ):
        with pytest.raises(HTTPException) as exc:
            decode_access_token("some_token")

    assert exc.value.status_code == 401
    assert exc.value.detail == "Type de token invalide"


# ============================================================================
# REFRESH TOKEN
# ============================================================================


def test_create_refresh_token():
    db = MagicMock()

    token = create_refresh_token(
        user_id=1,
        db=db,
    )

    assert isinstance(token, str)
    assert len(token) > 0

    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_validate_refresh_token_success():
    db = MagicMock()

    refresh_token = MagicMock()
    refresh_token.is_revoked = False
    refresh_token.expires_at = datetime.utcnow() + timedelta(days=1)

    db.query.return_value.filter.return_value.first.return_value = refresh_token

    result = validate_refresh_token(
        "valid_refresh_token",
        db,
    )

    assert result == refresh_token


def test_validate_refresh_token_not_found():
    db = MagicMock()

    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc:
        validate_refresh_token(
            "unknown_token",
            db,
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Refresh token invalide"


def test_validate_refresh_token_revoked():
    db = MagicMock()

    refresh_token = MagicMock()
    refresh_token.is_revoked = True
    refresh_token.expires_at = datetime.utcnow() + timedelta(days=1)

    db.query.return_value.filter.return_value.first.return_value = refresh_token

    with pytest.raises(HTTPException) as exc:
        validate_refresh_token(
            "revoked_token",
            db,
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Refresh token révoqué"


def test_validate_refresh_token_expired():
    db = MagicMock()

    refresh_token = MagicMock()
    refresh_token.is_revoked = False
    refresh_token.expires_at = datetime.utcnow() - timedelta(days=1)

    db.query.return_value.filter.return_value.first.return_value = refresh_token

    with pytest.raises(HTTPException) as exc:
        validate_refresh_token(
            "expired_token",
            db,
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Refresh token expiré"


# ============================================================================
# AUTHENTICATE USER
# ============================================================================


def test_authenticate_user_success():
    db = MagicMock()

    user = MagicMock()
    user.hashed_password = "hashed_password"

    db.query.return_value.filter.return_value.first.return_value = user

    with patch(
        "api.auth_utils.verify_password",
        return_value=True,
    ):
        result = authenticate_user(
            "test@example.com",
            "password123",
            db,
        )

    assert result == user


def test_authenticate_user_not_found():
    db = MagicMock()

    db.query.return_value.filter.return_value.first.return_value = None

    result = authenticate_user(
        "unknown@example.com",
        "password123",
        db,
    )

    assert result is None


def test_authenticate_user_wrong_password():
    db = MagicMock()

    user = MagicMock()
    user.hashed_password = "hashed_password"

    db.query.return_value.filter.return_value.first.return_value = user

    with patch(
        "api.auth_utils.verify_password",
        return_value=False,
    ):
        result = authenticate_user(
            "test@example.com",
            "wrong_password",
            db,
        )

    assert result is None


# ============================================================================
# GET CURRENT USER
# ============================================================================


@pytest.mark.asyncio
async def test_get_current_user_success():
    db = MagicMock()

    user = MagicMock()
    user.id = 1
    user.is_active = True

    db.query.return_value.filter.return_value.first.return_value = user

    with patch(
        "api.auth_utils.decode_access_token",
        return_value={"sub": "1"},
    ):
        result = await get_current_user(
            token="valid_token",
            db=db,
        )

    assert result == user


@pytest.mark.asyncio
async def test_get_current_user_missing_sub():
    db = MagicMock()

    with patch(
        "api.auth_utils.decode_access_token",
        return_value={},
    ):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(
                token="valid_token",
                db=db,
            )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Token invalide"


@pytest.mark.asyncio
async def test_get_current_user_invalid_sub():
    db = MagicMock()

    with patch(
        "api.auth_utils.decode_access_token",
        return_value={"sub": "abc"},
    ):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(
                token="valid_token",
                db=db,
            )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Token invalide"


@pytest.mark.asyncio
async def test_get_current_user_not_found():
    db = MagicMock()

    db.query.return_value.filter.return_value.first.return_value = None

    with patch(
        "api.auth_utils.decode_access_token",
        return_value={"sub": "1"},
    ):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(
                token="valid_token",
                db=db,
            )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Utilisateur introuvable"


@pytest.mark.asyncio
async def test_get_current_user_inactive():
    db = MagicMock()

    user = MagicMock()
    user.id = 1
    user.is_active = False

    db.query.return_value.filter.return_value.first.return_value = user

    with patch(
        "api.auth_utils.decode_access_token",
        return_value={"sub": "1"},
    ):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(
                token="valid_token",
                db=db,
            )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Compte désactivé"


# ============================================================================
# REVOKE TOKENS
# ============================================================================


def test_revoke_all_user_tokens():
    db = MagicMock()

    revoke_all_user_tokens(
        user_id=1,
        db=db,
    )

    db.query.assert_called_once()
    db.commit.assert_called_once()

    update_mock = (
        db.query.return_value
        .filter.return_value
        .update
    )

    update_mock.assert_called_once_with(
        {"is_revoked": True}
    )


def test_revoke_refresh_token_found():
    db = MagicMock()

    refresh_token = MagicMock()
    refresh_token.is_revoked = False

    db.query.return_value.filter.return_value.first.return_value = refresh_token

    revoke_refresh_token(
        "refresh_token",
        db,
    )

    assert refresh_token.is_revoked is True
    db.commit.assert_called_once()


def test_revoke_refresh_token_not_found():
    db = MagicMock()

    db.query.return_value.filter.return_value.first.return_value = None

    revoke_refresh_token(
        "unknown_token",
        db,
    )

    db.commit.assert_not_called()

