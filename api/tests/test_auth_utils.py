"""api/tests/test_auth_utils.py
Tests unitaires des briques d'authentification : hachage, jetons JWT,
refresh tokens et résolution de l'utilisateur courant.

Chaque cas de refus est testé séparément du cas nominal : c'est le refus qui
protège, et un `get_current_user` qui laisserait passer un compte désactivé ou
un jeton de mauvais type ne se verrait sur aucun test du chemin heureux.
"""

from datetime import datetime, timedelta

import pytest
from api.auth_config import JWT_ALGORITHM, JWT_SECRET_KEY

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

from database.tables.refresh_tokens import RefreshToken
from database.tables.users import User
from fastapi import HTTPException
from jose import jwt


@pytest.fixture
def utilisateur(db_session):
    """Utilisateur actif enregistré en base, mot de passe « motdepasse123 »."""
    user = User(
        email="lecteur@example.com",
        username="lecteur",
        hashed_password=hash_password("motdepasse123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Hachage du mot de passe
# ---------------------------------------------------------------------------


def test_hash_password_ne_rend_pas_le_mot_de_passe_en_clair():
    empreinte = hash_password("motdepasse123")

    assert empreinte != "motdepasse123"
    assert empreinte.startswith("$2b$")


def test_hash_password_produit_deux_empreintes_differentes_pour_le_meme_mot():
    """bcrypt tire un sel par appel : deux empreintes identiques permettraient
    de repérer en base les comptes partageant un mot de passe."""
    assert hash_password("motdepasse123") != hash_password("motdepasse123")


def test_verify_password_accepte_le_bon_mot_de_passe():
    assert verify_password("motdepasse123", hash_password("motdepasse123")) is True


def test_verify_password_refuse_un_mot_de_passe_different():
    assert verify_password("mauvais", hash_password("motdepasse123")) is False


# ---------------------------------------------------------------------------
# Access token
# ---------------------------------------------------------------------------


def test_create_access_token_puis_decode_rend_les_donnees_transmises():
    token = create_access_token(data={"sub": "42", "email": "a@b.fr"})

    payload = decode_access_token(token)

    assert payload["sub"] == "42"
    assert payload["email"] == "a@b.fr"
    assert payload["type"] == "access"


def test_decode_access_token_refuse_un_jeton_expire():
    token = create_access_token(data={"sub": "42"}, expires_delta=timedelta(seconds=-1))

    with pytest.raises(HTTPException) as erreur:
        decode_access_token(token)

    assert erreur.value.status_code == 401
    assert erreur.value.detail == "Token invalide ou expiré"


def test_decode_access_token_refuse_un_jeton_qui_nest_pas_de_type_access():
    """Un refresh token présenté comme access token doit être rejeté : sans
    cette vérification, un jeton à durée de vie longue ouvrirait les routes
    protégées."""
    token = jwt.encode(
        {"sub": "42", "type": "refresh", "exp": datetime.utcnow() + timedelta(hours=1)},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    with pytest.raises(HTTPException) as erreur:
        decode_access_token(token)

    assert erreur.value.status_code == 401
    assert erreur.value.detail == "Type de token invalide"


def test_decode_access_token_refuse_un_jeton_signe_avec_une_autre_cle():
    token = jwt.encode(
        {"sub": "42", "type": "access", "exp": datetime.utcnow() + timedelta(hours=1)},
        "une-autre-cle-de-signature",
        algorithm=JWT_ALGORITHM,
    )

    with pytest.raises(HTTPException) as erreur:
        decode_access_token(token)

    assert erreur.value.status_code == 401


def test_decode_access_token_refuse_une_chaine_qui_nest_pas_un_jwt():
    with pytest.raises(HTTPException) as erreur:
        decode_access_token("pas-un-jeton")

    assert erreur.value.status_code == 401


# ---------------------------------------------------------------------------
# Refresh token
# ---------------------------------------------------------------------------


def test_create_refresh_token_enregistre_le_jeton_en_base(db_session, utilisateur):
    token = create_refresh_token(utilisateur.id, db_session)

    enregistre = (
        db_session.query(RefreshToken).filter(RefreshToken.token == token).one()
    )
    assert enregistre.user_id == utilisateur.id
    assert enregistre.is_revoked is False
    assert enregistre.expires_at > datetime.utcnow()


def test_validate_refresh_token_rend_le_jeton_quand_il_est_valide(
    db_session, utilisateur
):
    token = create_refresh_token(utilisateur.id, db_session)

    assert validate_refresh_token(token, db_session).token == token


def test_validate_refresh_token_refuse_un_jeton_inconnu(db_session):
    with pytest.raises(HTTPException) as erreur:
        validate_refresh_token("jeton-jamais-emis", db_session)

    assert erreur.value.status_code == 401
    assert erreur.value.detail == "Refresh token invalide"


def test_validate_refresh_token_refuse_un_jeton_revoque(db_session, utilisateur):
    token = create_refresh_token(utilisateur.id, db_session)
    revoke_refresh_token(token, db_session)

    with pytest.raises(HTTPException) as erreur:
        validate_refresh_token(token, db_session)

    assert erreur.value.status_code == 401
    assert erreur.value.detail == "Refresh token révoqué"


def test_validate_refresh_token_refuse_un_jeton_expire(db_session, utilisateur):
    expire = RefreshToken(
        token="jeton-perime",
        user_id=utilisateur.id,
        expires_at=datetime.utcnow() - timedelta(days=1),
    )
    db_session.add(expire)
    db_session.commit()

    with pytest.raises(HTTPException) as erreur:
        validate_refresh_token("jeton-perime", db_session)

    assert erreur.value.status_code == 401
    assert erreur.value.detail == "Refresh token expiré"


def test_revoke_refresh_token_revoque_le_jeton_vise(db_session, utilisateur):
    token = create_refresh_token(utilisateur.id, db_session)

    revoke_refresh_token(token, db_session)

    assert (
        db_session.query(RefreshToken)
        .filter(RefreshToken.token == token)
        .one()
        .is_revoked
        is True
    )


def test_revoke_refresh_token_ignore_un_jeton_inconnu(db_session):
    """Révoquer un jeton absent n'est pas une erreur : la déconnexion d'un
    jeton déjà nettoyé doit rester silencieuse."""
    revoke_refresh_token("jeton-jamais-emis", db_session)

    assert db_session.query(RefreshToken).count() == 0


def test_revoke_all_user_tokens_revoque_tous_les_jetons_de_lutilisateur(
    db_session, utilisateur
):
    create_refresh_token(utilisateur.id, db_session)
    create_refresh_token(utilisateur.id, db_session)

    revoke_all_user_tokens(utilisateur.id, db_session)

    jetons = db_session.query(RefreshToken).all()
    assert len(jetons) == 2
    assert all(jeton.is_revoked for jeton in jetons)


def test_revoke_all_user_tokens_laisse_intacts_ceux_dun_autre_utilisateur(
    db_session, utilisateur
):
    autre = User(
        email="autre@example.com",
        username="autre",
        hashed_password=hash_password("motdepasse123"),
    )
    db_session.add(autre)
    db_session.commit()
    db_session.refresh(autre)
    jeton_autre = create_refresh_token(autre.id, db_session)
    create_refresh_token(utilisateur.id, db_session)

    revoke_all_user_tokens(utilisateur.id, db_session)

    conserve = (
        db_session.query(RefreshToken).filter(RefreshToken.token == jeton_autre).one()
    )
    assert conserve.is_revoked is False


# ---------------------------------------------------------------------------
# Authentification par email / mot de passe
# ---------------------------------------------------------------------------


def test_authenticate_user_rend_lutilisateur_avec_les_bons_identifiants(
    db_session, utilisateur
):
    trouve = authenticate_user("lecteur@example.com", "motdepasse123", db_session)

    assert trouve is not None
    assert trouve.id == utilisateur.id


def test_authenticate_user_refuse_un_email_inconnu(db_session):
    assert (
        authenticate_user("personne@example.com", "motdepasse123", db_session) is None
    )


def test_authenticate_user_refuse_un_mauvais_mot_de_passe(db_session, utilisateur):
    assert authenticate_user("lecteur@example.com", "mauvais", db_session) is None


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_user_rend_lutilisateur_du_jeton(db_session, utilisateur):
    token = create_access_token(data={"sub": str(utilisateur.id)})

    courant = await get_current_user(token=token, db=db_session)

    assert courant.id == utilisateur.id


@pytest.mark.asyncio
async def test_get_current_user_refuse_un_jeton_sans_claim_sub(db_session):
    token = create_access_token(data={"email": "a@b.fr"})

    with pytest.raises(HTTPException) as erreur:
        await get_current_user(token=token, db=db_session)

    assert erreur.value.status_code == 401
    assert erreur.value.detail == "Token invalide"


@pytest.mark.asyncio
async def test_get_current_user_refuse_un_sub_non_numerique(db_session):
    token = create_access_token(data={"sub": "pas-un-entier"})

    with pytest.raises(HTTPException) as erreur:
        await get_current_user(token=token, db=db_session)

    assert erreur.value.status_code == 401
    assert erreur.value.detail == "Token invalide"


@pytest.mark.asyncio
async def test_get_current_user_refuse_un_utilisateur_supprime(db_session):
    token = create_access_token(data={"sub": "9999"})

    with pytest.raises(HTTPException) as erreur:
        await get_current_user(token=token, db=db_session)

    assert erreur.value.status_code == 401
    assert erreur.value.detail == "Utilisateur introuvable"


@pytest.mark.asyncio
async def test_get_current_user_refuse_un_compte_desactive(db_session, utilisateur):
    utilisateur.is_active = False
    db_session.commit()
    token = create_access_token(data={"sub": str(utilisateur.id)})

    with pytest.raises(HTTPException) as erreur:
        await get_current_user(token=token, db=db_session)

    assert erreur.value.status_code == 403
    assert erreur.value.detail == "Compte désactivé"

