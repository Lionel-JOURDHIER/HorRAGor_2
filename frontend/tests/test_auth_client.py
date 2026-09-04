"""frontend/tests/test_auth_client.py
Tests du client HTTP d'authentification du frontend.

Le module ne contient pas de logique métier : sa responsabilité est de traduire
une réponse HTTP en valeur exploitable par Streamlit, et de ne jamais laisser
une exception réseau remonter jusqu'à l'interface. Ce sont donc les codes de
retour et les cas d'échec qui sont testés, pas le contenu des réponses.

`encrypt_password` est simulé partout : son propre comportement est vérifié
dans test_auth_crypto_client.py, et l'appeler ici ajouterait un appel réseau
à /auth/public-key.
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import auth_client

SESSION = {
    "user": {"id": 1, "email": "lecteur@example.com", "username": "lecteur"},
    "access_token": "jeton-acces",
    "refresh_token": "jeton-refresh",
}


def reponse(status_code, corps=None):
    """Construit un double de réponse `requests` au code et au corps voulus.

    Args:
        status_code: Code HTTP retourné.
        corps: Objet rendu par `.json()`, ignoré si le test ne le lit pas.

    Returns:
        Mock: double utilisable comme valeur de retour de requests.post/get.
    """
    mock = Mock()
    mock.status_code = status_code
    mock.json.return_value = corps
    return mock


@pytest.fixture(autouse=True)
def chiffrement_simule():
    """Remplace le chiffrement RSA par une transformation locale.

    Sans cela, chaque appel à login_user ou register_user irait chercher la clé
    publique sur l'API.
    """
    with patch(
        "utils.auth_client.encrypt_password", side_effect=lambda mdp: f"chiffre:{mdp}"
    ) as double:
        yield double


# ---------------------------------------------------------------------------
# login_user
# ---------------------------------------------------------------------------


def test_login_user_rend_la_session_quand_lapi_repond_200():
    with patch("utils.auth_client.requests.post", return_value=reponse(200, SESSION)):
        assert auth_client.login_user("lecteur@example.com", "motdepasse123") == SESSION


def test_login_user_envoie_le_mot_de_passe_chiffre_et_jamais_en_clair():
    with patch(
        "utils.auth_client.requests.post", return_value=reponse(200, SESSION)
    ) as post:
        auth_client.login_user("lecteur@example.com", "motdepasse123")

    envoye = post.call_args.kwargs["json"]
    assert envoye["password"] == "chiffre:motdepasse123"
    assert envoye["email"] == "lecteur@example.com"


@pytest.mark.parametrize("code", [400, 401, 422, 500])
def test_login_user_rend_none_sur_un_code_derreur(code):
    with patch("utils.auth_client.requests.post", return_value=reponse(code, {})):
        assert auth_client.login_user("lecteur@example.com", "motdepasse123") is None


def test_login_user_rend_none_quand_lapi_est_injoignable():
    with patch(
        "utils.auth_client.requests.post",
        side_effect=requests.exceptions.ConnectionError("API injoignable"),
    ):
        assert auth_client.login_user("lecteur@example.com", "motdepasse123") is None


def test_login_user_rend_none_quand_le_chiffrement_echoue(chiffrement_simule):
    """Une clé publique inaccessible ne doit pas faire remonter d'exception
    jusqu'à Streamlit, qui n'a pas de gestionnaire d'erreur global."""
    chiffrement_simule.side_effect = requests.exceptions.ConnectionError("pas de clé")

    assert auth_client.login_user("lecteur@example.com", "motdepasse123") is None


# ---------------------------------------------------------------------------
# register_user
# ---------------------------------------------------------------------------


def test_register_user_rend_la_session_quand_lapi_repond_201():
    with patch("utils.auth_client.requests.post", return_value=reponse(201, SESSION)):
        cree = auth_client.register_user(
            "lecteur@example.com", "lecteur", "motdepasse123"
        )

    assert cree == SESSION


def test_register_user_rend_none_sur_un_200_qui_nest_pas_un_201():
    """L'inscription est la seule route à répondre 201 : accepter un 200
    laisserait passer une réponse d'une autre route."""
    with patch("utils.auth_client.requests.post", return_value=reponse(200, SESSION)):
        assert (
            auth_client.register_user("lecteur@example.com", "lecteur", "motdepasse123")
            is None
        )


def test_register_user_transmet_les_trois_champs_avec_un_mot_de_passe_chiffre():
    with patch(
        "utils.auth_client.requests.post", return_value=reponse(201, SESSION)
    ) as post:
        auth_client.register_user("lecteur@example.com", "lecteur", "motdepasse123")

    assert post.call_args.kwargs["json"] == {
        "email": "lecteur@example.com",
        "username": "lecteur",
        "password": "chiffre:motdepasse123",
    }


@pytest.mark.parametrize("code", [400, 409, 422])
def test_register_user_rend_none_sur_un_refus_de_lapi(code):
    with patch("utils.auth_client.requests.post", return_value=reponse(code, {})):
        assert (
            auth_client.register_user("lecteur@example.com", "lecteur", "motdepasse123")
            is None
        )


def test_register_user_rend_none_quand_lapi_est_injoignable():
    with patch(
        "utils.auth_client.requests.post",
        side_effect=requests.exceptions.Timeout(),
    ):
        assert (
            auth_client.register_user("lecteur@example.com", "lecteur", "motdepasse123")
            is None
        )


# ---------------------------------------------------------------------------
# refresh_access_token
# ---------------------------------------------------------------------------


def test_refresh_access_token_rend_les_nouveaux_jetons():
    jetons = {"access_token": "nouveau", "refresh_token": "nouveau-refresh"}

    with patch("utils.auth_client.requests.post", return_value=reponse(200, jetons)):
        assert auth_client.refresh_access_token("jeton-refresh") == jetons


def test_refresh_access_token_rend_none_sur_un_jeton_refuse():
    with patch("utils.auth_client.requests.post", return_value=reponse(401, {})):
        assert auth_client.refresh_access_token("jeton-perime") is None


def test_refresh_access_token_rend_none_quand_lapi_est_injoignable():
    with patch(
        "utils.auth_client.requests.post",
        side_effect=requests.exceptions.ConnectionError("API injoignable"),
    ):
        assert auth_client.refresh_access_token("jeton-refresh") is None


# ---------------------------------------------------------------------------
# logout_user
# ---------------------------------------------------------------------------


def test_logout_user_rend_true_sur_un_204():
    with patch("utils.auth_client.requests.post", return_value=reponse(204)) as post:
        assert auth_client.logout_user("jeton-refresh", "jeton-acces") is True

    assert post.call_args.kwargs["headers"] == {"Authorization": "Bearer jeton-acces"}
    assert post.call_args.kwargs["json"] == {"refresh_token": "jeton-refresh"}


@pytest.mark.parametrize("code", [200, 401, 500])
def test_logout_user_rend_false_sur_tout_autre_code(code):
    with patch("utils.auth_client.requests.post", return_value=reponse(code)):
        assert auth_client.logout_user("jeton-refresh", "jeton-acces") is False


def test_logout_user_rend_false_quand_lapi_est_injoignable():
    """Une déconnexion qui échoue doit se voir : la session locale ne peut pas
    être considérée comme fermée si le refresh token reste valide en base."""
    with patch(
        "utils.auth_client.requests.post",
        side_effect=requests.exceptions.ConnectionError("API injoignable"),
    ):
        assert auth_client.logout_user("jeton-refresh", "jeton-acces") is False


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------


def test_get_current_user_rend_le_profil_sur_un_200():
    profil = {"id": 1, "email": "lecteur@example.com", "username": "lecteur"}

    with patch(
        "utils.auth_client.requests.get", return_value=reponse(200, profil)
    ) as g:
        assert auth_client.get_current_user("jeton-acces") == profil

    assert g.call_args.kwargs["headers"] == {"Authorization": "Bearer jeton-acces"}


@pytest.mark.parametrize("code", [401, 403, 500])
def test_get_current_user_rend_none_sur_un_refus(code):
    with patch("utils.auth_client.requests.get", return_value=reponse(code, {})):
        assert auth_client.get_current_user("jeton-invalide") is None


def test_get_current_user_rend_none_quand_lapi_est_injoignable():
    with patch(
        "utils.auth_client.requests.get",
        side_effect=requests.exceptions.Timeout(),
    ):
        assert auth_client.get_current_user("jeton-acces") is None
