<<<<<<< HEAD
import base64

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from api.auth_crypto import decrypt_password, get_public_key_pem, _public_key


def encrypt_password(password: str) -> str:
    """Chiffre un mot de passe avec la clé publique utilisée par l'API."""
    ciphertext = _public_key.encrypt(
        password.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(ciphertext).decode("utf-8")


def test_get_public_key_pem():
    result = get_public_key_pem()

    assert isinstance(result, str)
    assert "-----BEGIN" in result
    assert "PUBLIC KEY" in result
    assert "-----END" in result


def test_decrypt_password_success():
    encrypted = encrypt_password("Password123!")

    result = decrypt_password(encrypted)

    assert result == "Password123!"


def test_decrypt_password_invalid_base64():
    with pytest.raises(ValueError, match="Mot de passe chiffré invalide"):
        decrypt_password("not-valid-base64!!!")


def test_decrypt_password_invalid_ciphertext():
    encrypted = base64.b64encode(b"invalid ciphertext").decode("utf-8")

    with pytest.raises(ValueError, match="Mot de passe chiffré invalide"):
        decrypt_password(encrypted)


=======
"""api/tests/test_auth_crypto.py
Tests du chiffrement RSA du mot de passe transmis à /auth/login et /auth/register.

Ce chiffrement remplace le TLS absent du déploiement local : un défaut ici
laisserait passer un mot de passe en clair sur le réseau. Les tests portent
donc sur le contrat de `api/auth_crypto.py` — un aller-retour fidèle, et un
refus explicite de tout ce qui ne déchiffre pas — pas sur l'implémentation RSA
elle-même, qui est celle de la bibliothèque `cryptography`.
"""

import base64

import pytest
from api.auth_crypto import decrypt_password, get_public_key_pem
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

_OAEP = padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None,
)


def chiffrer_avec(pem: str, mot_de_passe: str) -> str:
    """Chiffre un mot de passe avec une clé publique PEM, comme le frontend.

    Args:
        pem: Clé publique au format PEM.
        mot_de_passe: Mot de passe en clair.

    Returns:
        Mot de passe chiffré, encodé en base64.
    """
    public_key = serialization.load_pem_public_key(pem.encode("utf-8"))
    return base64.b64encode(
        public_key.encrypt(mot_de_passe.encode("utf-8"), _OAEP)
    ).decode("utf-8")


def test_get_public_key_pem_retourne_une_cle_publique_exploitable():
    pem = get_public_key_pem()

    assert pem.startswith("-----BEGIN PUBLIC KEY-----")
    assert serialization.load_pem_public_key(pem.encode("utf-8")).key_size == 2048


@pytest.mark.parametrize(
    "mot_de_passe",
    [
        "motdepasse123",
        "Un mot de passe avec des espaces",
        "accentué-é&#@!",
        "a" * 100,
    ],
)
def test_aller_retour_chiffrement_rend_le_mot_de_passe_initial(mot_de_passe):
    chiffre = chiffrer_avec(get_public_key_pem(), mot_de_passe)

    assert decrypt_password(chiffre) == mot_de_passe


def test_chiffrement_du_meme_mot_de_passe_donne_deux_chiffres_differents():
    """OAEP tire un aléa par chiffrement : deux chiffrés identiques
    trahiraient un padding déterministe, donc un mot de passe reconnaissable
    d'une session à l'autre en écoutant le réseau."""
    pem = get_public_key_pem()

    assert chiffrer_avec(pem, "motdepasse123") != chiffrer_avec(pem, "motdepasse123")


def test_decrypt_password_refuse_un_base64_invalide():
    with pytest.raises(ValueError, match="Mot de passe chiffré invalide"):
        decrypt_password("ceci n'est pas du base64 !")


def test_decrypt_password_refuse_un_base64_valide_qui_nest_pas_un_chiffre():
    with pytest.raises(ValueError, match="Mot de passe chiffré invalide"):
        decrypt_password(base64.b64encode(b"nimporte quoi").decode("utf-8"))


def test_decrypt_password_refuse_un_chiffre_produit_avec_une_autre_cle():
    """Cas du redémarrage de l'API : la paire est régénérée en mémoire, un
    mot de passe chiffré avec la clé précédente ne doit pas déchiffrer."""
    autre_cle = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    autre_pem = (
        autre_cle.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )

    with pytest.raises(ValueError, match="Mot de passe chiffré invalide"):
        decrypt_password(chiffrer_avec(autre_pem, "motdepasse123"))
>>>>>>> a1ffb27804cd844cab2d1ad18bf22b502d0e4749
