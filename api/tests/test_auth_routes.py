
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from api.auth_routes import (
    get_me,
    get_public_key,
    login,
    login_for_swagger,
    logout,
    logout_all,
    refresh_token,
    register,
)
from api.schemas import TokenRefresh, UserLogin, UserRegister
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = 1
    user.email = "test@example.com"
    user.username = "testuser"
    user.is_active = True
    user.is_verified = True
    user.created_at = datetime.now()
    return user


@pytest.fixture
def mock_db():
    return MagicMock()


# ---------------------------------------------------------------------------
# GET /auth/public-key
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_public_key():
    with patch(
        "api.auth_routes.get_public_key_pem",
        return_value="PUBLIC_KEY_TEST",
    ):
        result = await get_public_key()

    assert result == {"public_key": "PUBLIC_KEY_TEST"}


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_success(mock_db):
    user_data = UserRegister(
        email="test@example.com",
        username="testuser",
        password="encrypted_password",
    )

    mock_db.query.return_value.filter.return_value.first.return_value = None

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user.username = "testuser"
    mock_user.is_active = True
    mock_user.is_verified = False
    mock_user.created_at = datetime.now()

    with (
        patch("api.auth_routes.decrypt_password", return_value="password123"),
        patch("api.auth_routes.hash_password", return_value="hashed"),
        patch(
            "api.auth_routes.create_access_token",
            return_value="access_token",
        ),
        patch(
            "api.auth_routes.create_refresh_token",
            return_value="refresh_token",
        ),
        patch("api.auth_routes.User", return_value=mock_user),
    ):
        mock_db.refresh.side_effect = lambda user: None

        result = await register(user_data, mock_db)

    assert result.user.email == "test@example.com"
    assert result.user.username == "testuser"
    assert result.access_token == "access_token"
    assert result.refresh_token == "refresh_token"

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_register_invalid_encrypted_password(mock_db):
    user_data = UserRegister(
        email="test@example.com",
        username="testuser",
        password="invalid",
    )

    with patch(
        "api.auth_routes.decrypt_password",
        side_effect=ValueError,
    ):
        with pytest.raises(HTTPException) as exc:
            await register(user_data, mock_db)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Mot de passe chiffré invalide"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "password",
    [
        "short",
        "a" * 101,
    ],
)
async def test_register_invalid_password_length(mock_db, password):
    user_data = UserRegister(
        email="test@example.com",
        username="testuser",
        password="encrypted",
    )

    with patch(
        "api.auth_routes.decrypt_password",
        return_value=password,
    ):
        with pytest.raises(HTTPException) as exc:
            await register(user_data, mock_db)

    assert exc.value.status_code == 400
    assert (
        exc.value.detail
        == "Le mot de passe doit contenir entre 8 et 100 caractères"
    )


@pytest.mark.asyncio
async def test_register_email_already_exists(mock_db):
    user_data = UserRegister(
        email="existing@example.com",
        username="testuser",
        password="encrypted",
    )

    existing_user = MagicMock()

    mock_db.query.return_value.filter.return_value.first.return_value = (
        existing_user
    )

    with patch(
        "api.auth_routes.decrypt_password",
        return_value="password123",
    ):
        with pytest.raises(HTTPException) as exc:
            await register(user_data, mock_db)

    assert exc.value.status_code == 409
    assert exc.value.detail == "Un compte avec cet email existe déjà"


@pytest.mark.asyncio
async def test_register_username_already_exists(mock_db):
    user_data = UserRegister(
        email="new@example.com",
        username="existinguser",
        password="encrypted",
    )

    # Premier appel : email inexistant
    # Deuxième appel : username existant
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        None,
        MagicMock(),
    ]

    with patch(
        "api.auth_routes.decrypt_password",
        return_value="password123",
    ):
        with pytest.raises(HTTPException) as exc:
            await register(user_data, mock_db)

    assert exc.value.status_code == 409
    assert exc.value.detail == "Ce nom d'utilisateur est déjà pris"


@pytest.mark.asyncio
async def test_register_integrity_error(mock_db):
    user_data = UserRegister(
        email="test@example.com",
        username="testuser",
        password="encrypted",
    )

    mock_db.query.return_value.filter.return_value.first.return_value = None

    mock_db.commit.side_effect = IntegrityError(
        "statement",
        "params",
        Exception("database error"),
    )

    with (
        patch(
            "api.auth_routes.decrypt_password",
            return_value="password123",
        ),
        patch("api.auth_routes.hash_password", return_value="hashed"),
    ):
        with pytest.raises(HTTPException) as exc:
            await register(user_data, mock_db)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Erreur lors de la création du compte"

    mock_db.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success(mock_db, mock_user):
    credentials = UserLogin(
        email="test@example.com",
        password="encrypted_password",
    )

    with (
        patch(
            "api.auth_routes.decrypt_password",
            return_value="password123",
        ),
        patch(
            "api.auth_routes.authenticate_user",
            return_value=mock_user,
        ),
        patch(
            "api.auth_routes.create_access_token",
            return_value="access_token",
        ),
        patch(
            "api.auth_routes.create_refresh_token",
            return_value="refresh_token",
        ),
    ):
        result = await login(credentials, mock_db)

    assert result.user.email == "test@example.com"
    assert result.access_token == "access_token"
    assert result.refresh_token == "refresh_token"


@pytest.mark.asyncio
async def test_login_invalid_encrypted_password(mock_db):
    credentials = UserLogin(
        email="test@example.com",
        password="invalid",
    )

    with patch(
        "api.auth_routes.decrypt_password",
        side_effect=ValueError,
    ):
        with pytest.raises(HTTPException) as exc:
            await login(credentials, mock_db)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Mot de passe chiffré invalide"


@pytest.mark.asyncio
async def test_login_invalid_credentials(mock_db):
    credentials = UserLogin(
        email="test@example.com",
        password="encrypted",
    )

    with (
        patch(
            "api.auth_routes.decrypt_password",
            return_value="password123",
        ),
        patch(
            "api.auth_routes.authenticate_user",
            return_value=None,
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await login(credentials, mock_db)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Email ou mot de passe incorrect"


# ---------------------------------------------------------------------------
# POST /auth/token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_for_swagger_success(mock_db, mock_user):
    form_data = OAuth2PasswordRequestForm(
        username="test@example.com",
        password="password123",
    )

    with (
        patch(
            "api.auth_routes.authenticate_user",
            return_value=mock_user,
        ),
        patch(
            "api.auth_routes.create_access_token",
            return_value="access_token",
        ),
        patch(
            "api.auth_routes.create_refresh_token",
            return_value="refresh_token",
        ),
    ):
        result = await login_for_swagger(form_data, mock_db)

    assert result.access_token == "access_token"
    assert result.refresh_token == "refresh_token"


@pytest.mark.asyncio
async def test_login_for_swagger_invalid_credentials(mock_db):
    form_data = OAuth2PasswordRequestForm(
        username="test@example.com",
        password="wrong",
    )

    with patch(
        "api.auth_routes.authenticate_user",
        return_value=None,
    ):
        with pytest.raises(HTTPException) as exc:
            await login_for_swagger(form_data, mock_db)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Email ou mot de passe incorrect"


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_token_success(mock_db, mock_user):
    token_data = TokenRefresh(refresh_token="old_refresh_token")

    refresh_obj = MagicMock()
    refresh_obj.user_id = 1

    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    with (
        patch(
            "api.auth_routes.validate_refresh_token",
            return_value=refresh_obj,
        ),
        patch(
            "api.auth_routes.revoke_refresh_token",
        ) as mock_revoke,
        patch(
            "api.auth_routes.create_access_token",
            return_value="new_access_token",
        ),
        patch(
            "api.auth_routes.create_refresh_token",
            return_value="new_refresh_token",
        ),
    ):
        result = await refresh_token(token_data, mock_db)

    assert result.access_token == "new_access_token"
    assert result.refresh_token == "new_refresh_token"

    mock_revoke.assert_called_once_with(
        "old_refresh_token",
        mock_db,
    )


@pytest.mark.asyncio
async def test_refresh_token_user_not_found(mock_db):
    token_data = TokenRefresh(refresh_token="refresh_token")

    refresh_obj = MagicMock()
    refresh_obj.user_id = 999

    mock_db.query.return_value.filter.return_value.first.return_value = None

    with patch(
        "api.auth_routes.validate_refresh_token",
        return_value=refresh_obj,
    ):
        with pytest.raises(HTTPException) as exc:
            await refresh_token(token_data, mock_db)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Utilisateur introuvable ou inactif"


@pytest.mark.asyncio
async def test_refresh_token_inactive_user(mock_db, mock_user):
    token_data = TokenRefresh(refresh_token="refresh_token")

    mock_user.is_active = False

    refresh_obj = MagicMock()
    refresh_obj.user_id = 1

    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    with patch(
        "api.auth_routes.validate_refresh_token",
        return_value=refresh_obj,
    ):
        with pytest.raises(HTTPException) as exc:
            await refresh_token(token_data, mock_db)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Utilisateur introuvable ou inactif"


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout(mock_db, mock_user):
    token_data = TokenRefresh(refresh_token="refresh_token")

    with patch(
        "api.auth_routes.revoke_refresh_token"
    ) as mock_revoke:
        result = await logout(
            token_data,
            mock_user,
            mock_db,
        )

    assert result is None

    mock_revoke.assert_called_once_with(
        "refresh_token",
        mock_db,
    )


# ---------------------------------------------------------------------------
# POST /auth/logout-all
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_all(mock_db, mock_user):
    with patch(
        "api.auth_routes.revoke_all_user_tokens"
    ) as mock_revoke:
        result = await logout_all(
            mock_user,
            mock_db,
        )

    assert result is None

    mock_revoke.assert_called_once_with(
        mock_user.id,
        mock_db,
    )


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_me(mock_user):
    result = await get_me(mock_user)

    assert result.id == mock_user.id
    assert result.email == mock_user.email
    assert result.username == mock_user.username
    assert result.is_active == mock_user.is_active
    assert result.is_verified == mock_user.is_verified
    assert result.created_at == mock_user.created_at
