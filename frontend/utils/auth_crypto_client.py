"""frontend/utils/auth_crypto_client.py
Chiffrement du mot de passe avant envoi à l'API, côté client.

Compense en clair l'absence de TLS sur le déploiement local (voir CLAUDE.md,
section Pièges déjà payés) : chiffre uniquement le champ mot de passe envoyé
à /auth/login et /auth/register, avec la clé publique RSA exposée par
GET /auth/public-key (voir api/auth_crypto.py, même schéma RSA-OAEP/SHA-256).
"""

import base64

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from utils.api_client import get_api_url

_OAEP_PADDING = padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None,
)


def encrypt_password(password: str) -> str:
    """Chiffre un mot de passe avec la clé publique RSA courante de l'API.

    Récupère la clé publique à chaque appel plutôt que de la mettre en cache :
    l'API en génère une nouvelle à chaque redémarrage, la garder en cache
    exposerait à un échec de déchiffrement après un redémarrage de l'API.

    Args:
        password: Mot de passe en clair saisi par l'utilisateur.

    Returns:
        Mot de passe chiffré (RSA-OAEP/SHA-256), encodé en base64.

    Raises:
        requests.RequestException: Si la clé publique n'a pas pu être récupérée.
    """
    response = requests.get(f"{get_api_url()}/auth/public-key", timeout=10)
    response.raise_for_status()
    public_key = serialization.load_pem_public_key(
        response.json()["public_key"].encode("utf-8")
    )

    ciphertext = public_key.encrypt(password.encode("utf-8"), _OAEP_PADDING)
    return base64.b64encode(ciphertext).decode("utf-8")
