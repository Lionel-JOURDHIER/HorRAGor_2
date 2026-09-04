<<<<<<< HEAD

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
=======
"""api/tests/test_auth_routes.py
Tests des routes /auth/* par TestClient, contre une base SQLite en mémoire.

Couvre le flux d'authentification complet exigé par l'Épilogue MLOps
(inscription → connexion → accès à une route protégée → rafraîchissement →
déconnexion), puis chaque refus séparément. Aucun appel réseau ni base réelle :
`get_db` est remplacée par la session de test, et le mot de passe est chiffré
avec la clé publique réellement exposée par l'API.
"""

import base64

import pytest
from api.auth_utils import hash_password
from conftest import chiffrer
from database.tables.refresh_tokens import RefreshToken
from database.tables.users import User


@pytest.fixture
def compte(db_session):
    """Compte actif déjà inscrit, mot de passe en clair « motdepasse123 »."""
    user = User(
        email="lecteur@example.com",
        username="lecteur",
        hashed_password=hash_password("motdepasse123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def connecter(auth_client, email="lecteur@example.com", mot_de_passe="motdepasse123"):
    """Connecte un compte et retourne le corps de la réponse /auth/login.

    Args:
        auth_client: TestClient branché sur la base de test.
        email: Email du compte.
        mot_de_passe: Mot de passe en clair, chiffré avant envoi.

    Returns:
        dict: Corps JSON de la réponse, contenant user et les deux jetons.
    """
    reponse = auth_client.post(
        "/auth/login", json={"email": email, "password": chiffrer(mot_de_passe)}
    )
    assert reponse.status_code == 200
    return reponse.json()


# ---------------------------------------------------------------------------
# Flux complet
# ---------------------------------------------------------------------------


def test_flux_complet_inscription_connexion_profil_rafraichissement_deconnexion(
    auth_client, db_session
):
    """Le chemin critique de bout en bout, dans l'ordre où un utilisateur le
    parcourt. Chaque étape est vérifiée séparément par ailleurs ; ce test
    garantit qu'elles s'enchaînent."""
    inscription = auth_client.post(
        "/auth/register",
        json={
            "email": "nouveau@example.com",
            "username": "nouveau",
            "password": chiffrer("motdepasse123"),
        },
    )
    assert inscription.status_code == 201

    connexion = connecter(auth_client, "nouveau@example.com")
    access_token = connexion["access_token"]
    refresh_token = connexion["refresh_token"]

    profil = auth_client.get(
        "/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert profil.status_code == 200
    assert profil.json()["email"] == "nouveau@example.com"

    rafraichi = auth_client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert rafraichi.status_code == 200
    nouveau_refresh = rafraichi.json()["refresh_token"]
    assert nouveau_refresh != refresh_token

    deconnexion = auth_client.post(
        "/auth/logout",
        json={"refresh_token": nouveau_refresh},
        headers={"Authorization": f"Bearer {rafraichi.json()['access_token']}"},
    )
    assert deconnexion.status_code == 204

    apres_deconnexion = auth_client.post(
        "/auth/refresh", json={"refresh_token": nouveau_refresh}
    )
    assert apres_deconnexion.status_code == 401
>>>>>>> a1ffb27804cd844cab2d1ad18bf22b502d0e4749


# ---------------------------------------------------------------------------
# GET /auth/public-key
# ---------------------------------------------------------------------------

<<<<<<< HEAD
@pytest.mark.asyncio
async def test_get_public_key():
    with patch(
        "api.auth_routes.get_public_key_pem",
        return_value="PUBLIC_KEY_TEST",
    ):
        result = await get_public_key()

    assert result == {"public_key": "PUBLIC_KEY_TEST"}
=======

def test_public_key_expose_une_cle_publique_pem(auth_client):
    reponse = auth_client.get("/auth/public-key")

    assert reponse.status_code == 200
    assert reponse.json()["public_key"].startswith("-----BEGIN PUBLIC KEY-----")
>>>>>>> a1ffb27804cd844cab2d1ad18bf22b502d0e4749


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

<<<<<<< HEAD
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
=======

def test_register_cree_le_compte_et_rend_les_deux_jetons(auth_client, db_session):
    reponse = auth_client.post(
        "/auth/register",
        json={
            "email": "nouveau@example.com",
            "username": "nouveau",
            "password": chiffrer("motdepasse123"),
        },
    )

    assert reponse.status_code == 201
    corps = reponse.json()
    assert corps["user"]["email"] == "nouveau@example.com"
    assert corps["user"]["is_active"] is True
    assert corps["access_token"] and corps["refresh_token"]
    assert (
        db_session.query(User).filter(User.email == "nouveau@example.com").count() == 1
    )


def test_register_ne_stocke_jamais_le_mot_de_passe_en_clair(auth_client, db_session):
    auth_client.post(
        "/auth/register",
        json={
            "email": "nouveau@example.com",
            "username": "nouveau",
            "password": chiffrer("motdepasse123"),
        },
    )

    cree = db_session.query(User).filter(User.email == "nouveau@example.com").one()
    assert cree.hashed_password != "motdepasse123"
    assert cree.hashed_password.startswith("$2b$")


def test_register_ne_renvoie_pas_le_mot_de_passe_dans_la_reponse(auth_client):
    reponse = auth_client.post(
        "/auth/register",
        json={
            "email": "nouveau@example.com",
            "username": "nouveau",
            "password": chiffrer("motdepasse123"),
        },
    )

    assert "password" not in reponse.json()["user"]
    assert "hashed_password" not in reponse.json()["user"]


def test_register_refuse_un_mot_de_passe_non_chiffre(auth_client):
    """Un mot de passe envoyé en clair doit être refusé, pas accepté tel quel :
    l'accepter reviendrait à annuler en silence le chiffrement de transport."""
    reponse = auth_client.post(
        "/auth/register",
        json={
            "email": "nouveau@example.com",
            "username": "nouveau",
            "password": "motdepasse123",
        },
    )

    assert reponse.status_code == 400
    assert reponse.json()["detail"] == "Mot de passe chiffré invalide"


@pytest.mark.parametrize("longueur", [7, 101])
def test_register_refuse_un_mot_de_passe_hors_bornes(auth_client, longueur):
    """Les bornes portent sur le mot de passe déchiffré : le schéma Pydantic ne
    voit que le chiffré, dont la longueur ne dit rien de celle du clair."""
    reponse = auth_client.post(
        "/auth/register",
        json={
            "email": "nouveau@example.com",
            "username": "nouveau",
            "password": chiffrer("a" * longueur),
        },
    )

    assert reponse.status_code == 400
    assert "entre 8 et 100 caractères" in reponse.json()["detail"]


def test_register_refuse_un_email_deja_utilise(auth_client, compte):
    reponse = auth_client.post(
        "/auth/register",
        json={
            "email": "lecteur@example.com",
            "username": "un-autre-nom",
            "password": chiffrer("motdepasse123"),
        },
    )

    assert reponse.status_code == 409
    assert reponse.json()["detail"] == "Un compte avec cet email existe déjà"


def test_register_refuse_un_username_deja_pris(auth_client, compte):
    reponse = auth_client.post(
        "/auth/register",
        json={
            "email": "un-autre@example.com",
            "username": "lecteur",
            "password": chiffrer("motdepasse123"),
        },
    )

    assert reponse.status_code == 409
    assert reponse.json()["detail"] == "Ce nom d'utilisateur est déjà pris"


def test_register_refuse_un_email_mal_forme(auth_client):
    """Contrôle assuré par le motif du schéma Pydantic : 422 et non 400."""
    reponse = auth_client.post(
        "/auth/register",
        json={
            "email": "pas-un-email",
            "username": "nouveau",
            "password": chiffrer("motdepasse123"),
        },
    )

    assert reponse.status_code == 422
>>>>>>> a1ffb27804cd844cab2d1ad18bf22b502d0e4749


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

<<<<<<< HEAD
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
=======

def test_login_rend_lutilisateur_et_les_deux_jetons(auth_client, compte):
    corps = connecter(auth_client)

    assert corps["user"]["id"] == compte.id
    assert corps["user"]["username"] == "lecteur"
    assert corps["token_type"] == "bearer"
    assert corps["access_token"] and corps["refresh_token"]


def test_login_refuse_un_mauvais_mot_de_passe(auth_client, compte):
    reponse = auth_client.post(
        "/auth/login",
        json={"email": "lecteur@example.com", "password": chiffrer("mauvais-mot")},
    )

    assert reponse.status_code == 401
    assert reponse.json()["detail"] == "Email ou mot de passe incorrect"


def test_login_refuse_un_email_inconnu(auth_client):
    reponse = auth_client.post(
        "/auth/login",
        json={"email": "personne@example.com", "password": chiffrer("motdepasse123")},
    )

    assert reponse.status_code == 401
    assert reponse.json()["detail"] == "Email ou mot de passe incorrect"


def test_login_ne_distingue_pas_email_inconnu_et_mauvais_mot_de_passe(
    auth_client, compte
):
    """Deux messages différents permettraient d'énumérer les comptes existants."""
    inconnu = auth_client.post(
        "/auth/login",
        json={"email": "personne@example.com", "password": chiffrer("motdepasse123")},
    )
    mauvais = auth_client.post(
        "/auth/login",
        json={"email": "lecteur@example.com", "password": chiffrer("mauvais-mot")},
    )

    assert inconnu.json() == mauvais.json()


def test_login_refuse_un_mot_de_passe_non_chiffre(auth_client, compte):
    reponse = auth_client.post(
        "/auth/login",
        json={"email": "lecteur@example.com", "password": "motdepasse123"},
    )

    assert reponse.status_code == 400
    assert reponse.json()["detail"] == "Mot de passe chiffré invalide"


def test_login_refuse_un_chiffre_illisible(auth_client, compte):
    reponse = auth_client.post(
        "/auth/login",
        json={
            "email": "lecteur@example.com",
            "password": base64.b64encode(b"nimporte quoi").decode("utf-8"),
        },
    )

    assert reponse.status_code == 400


# ---------------------------------------------------------------------------
# POST /auth/token (formulaire OAuth2 de Swagger)
# ---------------------------------------------------------------------------


def test_token_accepte_le_formulaire_oauth2_avec_un_mot_de_passe_en_clair(
    auth_client, compte
):
    """Cette route alimente le bouton « Authorize » de Swagger, qui n'envoie
    pas de mot de passe chiffré — contrairement à /auth/login."""
    reponse = auth_client.post(
        "/auth/token",
        data={"username": "lecteur@example.com", "password": "motdepasse123"},
    )

    assert reponse.status_code == 200
    assert reponse.json()["token_type"] == "bearer"
    assert reponse.json()["access_token"]


def test_token_refuse_de_mauvais_identifiants(auth_client, compte):
    reponse = auth_client.post(
        "/auth/token",
        data={"username": "lecteur@example.com", "password": "mauvais-mot"},
    )

    assert reponse.status_code == 401
>>>>>>> a1ffb27804cd844cab2d1ad18bf22b502d0e4749


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------

<<<<<<< HEAD
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
=======

def test_refresh_rend_de_nouveaux_jetons_et_revoque_lancien(
    auth_client, db_session, compte
):
    ancien = connecter(auth_client)["refresh_token"]

    reponse = auth_client.post("/auth/refresh", json={"refresh_token": ancien})

    assert reponse.status_code == 200
    assert reponse.json()["refresh_token"] != ancien
    revoque = db_session.query(RefreshToken).filter(RefreshToken.token == ancien).one()
    assert revoque.is_revoked is True


def test_refresh_refuse_un_jeton_inconnu(auth_client):
    reponse = auth_client.post(
        "/auth/refresh", json={"refresh_token": "jeton-jamais-emis"}
    )

    assert reponse.status_code == 401
    assert reponse.json()["detail"] == "Refresh token invalide"


def test_refresh_refuse_un_jeton_deja_utilise(auth_client, compte):
    """Rejouer un refresh token déjà échangé doit échouer : il est révoqué au
    moment de l'échange, ce qui limite la fenêtre d'un jeton intercepté."""
    ancien = connecter(auth_client)["refresh_token"]
    auth_client.post("/auth/refresh", json={"refresh_token": ancien})

    rejoue = auth_client.post("/auth/refresh", json={"refresh_token": ancien})

    assert rejoue.status_code == 401
    assert rejoue.json()["detail"] == "Refresh token révoqué"


def test_refresh_refuse_le_jeton_dun_compte_desactive(auth_client, db_session, compte):
    refresh_token = connecter(auth_client)["refresh_token"]
    compte.is_active = False
    db_session.commit()

    reponse = auth_client.post("/auth/refresh", json={"refresh_token": refresh_token})

    assert reponse.status_code == 401
    assert reponse.json()["detail"] == "Utilisateur introuvable ou inactif"
>>>>>>> a1ffb27804cd844cab2d1ad18bf22b502d0e4749


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

<<<<<<< HEAD
@pytest.mark.asyncio
async def test_get_me(mock_user):
    result = await get_me(mock_user)

    assert result.id == mock_user.id
    assert result.email == mock_user.email
    assert result.username == mock_user.username
    assert result.is_active == mock_user.is_active
    assert result.is_verified == mock_user.is_verified
    assert result.created_at == mock_user.created_at
=======

def test_me_rend_le_profil_sans_donnee_sensible(auth_client, compte):
    access_token = connecter(auth_client)["access_token"]

    reponse = auth_client.get(
        "/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert reponse.status_code == 200
    assert reponse.json() == {
        "id": compte.id,
        "email": "lecteur@example.com",
        "username": "lecteur",
        "is_active": True,
        "is_verified": False,
        "created_at": reponse.json()["created_at"],
    }


def test_me_refuse_une_requete_sans_jeton(auth_client):
    reponse = auth_client.get("/auth/me")

    assert reponse.status_code == 401


def test_me_refuse_un_jeton_invalide(auth_client):
    reponse = auth_client.get(
        "/auth/me", headers={"Authorization": "Bearer pas-un-jeton"}
    )

    assert reponse.status_code == 401


# ---------------------------------------------------------------------------
# POST /auth/logout et /auth/logout-all
# ---------------------------------------------------------------------------


def test_logout_revoque_le_jeton_transmis(auth_client, db_session, compte):
    session = connecter(auth_client)

    reponse = auth_client.post(
        "/auth/logout",
        json={"refresh_token": session["refresh_token"]},
        headers={"Authorization": f"Bearer {session['access_token']}"},
    )

    assert reponse.status_code == 204
    revoque = (
        db_session.query(RefreshToken)
        .filter(RefreshToken.token == session["refresh_token"])
        .one()
    )
    assert revoque.is_revoked is True


def test_logout_refuse_une_requete_sans_jeton_daccess(auth_client, compte):
    session = connecter(auth_client)

    reponse = auth_client.post(
        "/auth/logout", json={"refresh_token": session["refresh_token"]}
    )

    assert reponse.status_code == 401


def test_logout_all_revoque_toutes_les_sessions_du_compte(
    auth_client, db_session, compte
):
    premiere = connecter(auth_client)
    connecter(auth_client)

    reponse = auth_client.post(
        "/auth/logout-all",
        headers={"Authorization": f"Bearer {premiere['access_token']}"},
    )

    assert reponse.status_code == 204
    jetons = db_session.query(RefreshToken).all()
    assert len(jetons) == 2
    assert all(jeton.is_revoked for jeton in jetons)
>>>>>>> a1ffb27804cd844cab2d1ad18bf22b502d0e4749
