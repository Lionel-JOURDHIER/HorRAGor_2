"""frontend/tests/test_auth_crypto_client.py
Tests du chiffrement du mot de passe côté client.

Ce chiffrement remplace le TLS absent du déploiement local : ce qui compte
n'est pas seulement qu'il produise une chaîne, mais que cette chaîne soit
déchiffrable par la clé privée correspondante, et que l'échec de récupération
de la clé publique remonte au lieu d'envoyer un mot de passe en clair.
"""

import base64
import os
import sys
from unittest.mock import Mock, patch

import pytest
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import auth_crypto_client

_OAEP = padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None,
)


@pytest.fixture
def paire_de_cles():
    """Paire RSA 2048 bits jouant le rôle de celle générée par l'API."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def reponse_cle_publique(paire_de_cles):
    """Mock de GET /auth/public-key exposant la clé publique de la fixture."""
    pem = (
        paire_de_cles.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    mock = Mock()
    mock.json.return_value = {"public_key": pem}
    mock.raise_for_status = Mock()
    return mock


def test_encrypt_password_produit_un_chiffre_dechiffrable_par_la_cle_privee(
    paire_de_cles, reponse_cle_publique
):
    with patch(
        "utils.auth_crypto_client.requests.get", return_value=reponse_cle_publique
    ):
        chiffre = auth_crypto_client.encrypt_password("motdepasse123")

    clair = paire_de_cles.decrypt(base64.b64decode(chiffre), _OAEP)
    assert clair.decode("utf-8") == "motdepasse123"


def test_encrypt_password_ne_laisse_pas_le_mot_de_passe_lisible(
    paire_de_cles, reponse_cle_publique
):
    with patch(
        "utils.auth_crypto_client.requests.get", return_value=reponse_cle_publique
    ):
        chiffre = auth_crypto_client.encrypt_password("motdepasse123")

    assert "motdepasse123" not in chiffre
    assert base64.b64decode(chiffre) != b"motdepasse123"


def test_encrypt_password_produit_deux_chiffres_differents_pour_le_meme_mot(
    paire_de_cles, reponse_cle_publique
):
    """OAEP tire un aléa par chiffrement : deux chiffrés identiques
    permettraient de reconnaître un mot de passe déjà observé."""
    with patch(
        "utils.auth_crypto_client.requests.get", return_value=reponse_cle_publique
    ):
        premier = auth_crypto_client.encrypt_password("motdepasse123")
        second = auth_crypto_client.encrypt_password("motdepasse123")

    assert premier != second


@pytest.mark.parametrize(
    "mot_de_passe", ["motdepasse123", "Accentué-éàü!", "a" * 100, "  espaces  "]
)
def test_encrypt_password_preserve_le_mot_de_passe_quel_que_soit_son_contenu(
    mot_de_passe, paire_de_cles, reponse_cle_publique
):
    with patch(
        "utils.auth_crypto_client.requests.get", return_value=reponse_cle_publique
    ):
        chiffre = auth_crypto_client.encrypt_password(mot_de_passe)

    assert (
        paire_de_cles.decrypt(base64.b64decode(chiffre), _OAEP).decode() == mot_de_passe
    )


def test_encrypt_password_interroge_la_cle_a_chaque_appel(
    paire_de_cles, reponse_cle_publique
):
    """L'API régénère sa paire à chaque redémarrage : une clé mise en cache
    ferait échouer le déchiffrement côté serveur sans message clair."""
    with patch(
        "utils.auth_crypto_client.requests.get", return_value=reponse_cle_publique
    ) as appel:
        auth_crypto_client.encrypt_password("motdepasse123")
        auth_crypto_client.encrypt_password("motdepasse123")

    assert appel.call_count == 2


def test_encrypt_password_propage_lechec_de_recuperation_de_la_cle():
    """Une API injoignable doit faire remonter l'erreur : la rattraper ici
    reviendrait à envoyer le mot de passe en clair ou à masquer la panne."""
    with patch(
        "utils.auth_crypto_client.requests.get",
        side_effect=requests.exceptions.ConnectionError("API injoignable"),
    ):
        with pytest.raises(requests.exceptions.ConnectionError):
            auth_crypto_client.encrypt_password("motdepasse123")


def test_encrypt_password_propage_une_reponse_en_erreur():
    mock = Mock()
    mock.raise_for_status.side_effect = requests.exceptions.HTTPError("500")

    with patch("utils.auth_crypto_client.requests.get", return_value=mock):
        with pytest.raises(requests.exceptions.HTTPError):
            auth_crypto_client.encrypt_password("motdepasse123")
