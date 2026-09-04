"""api/auth_crypto.py
Chiffrement RSA du mot de passe transmis à /auth/login et /auth/register.

Compense en clair l'absence de TLS sur le déploiement local (voir CLAUDE.md,
section Pièges déjà payés) : seul le champ mot de passe est protégé, pas le
reste des échanges (jeton JWT compris). La paire de clés est générée en
mémoire au démarrage du processus API et n'est jamais persistée — elle ne
protège que l'échange à la connexion, pas les comptes déjà en base, donc sa
rotation à chaque redémarrage n'a aucune conséquence côté données.
"""

import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

_OAEP_PADDING = padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None,
)

_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()


def get_public_key_pem() -> str:
    """Retourne la clé publique RSA au format PEM.

    Returns:
        Clé publique encodée PEM (SubjectPublicKeyInfo), exposée via
        GET /auth/public-key pour que le frontend chiffre le mot de passe
        avant envoi.
    """
    return _public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def decrypt_password(encrypted_b64: str) -> str:
    """Déchiffre un mot de passe chiffré côté client (RSA-OAEP/SHA-256).

    Args:
        encrypted_b64: Mot de passe chiffré avec la clé publique courante,
            encodé en base64.

    Returns:
        Mot de passe en clair.

    Raises:
        ValueError: Si le contenu n'est pas un base64 valide, ou ne déchiffre
            pas avec la clé privée courante (mauvaise clé, données corrompues).
    """
    try:
        ciphertext = base64.b64decode(encrypted_b64, validate=True)
        plaintext = _private_key.decrypt(ciphertext, _OAEP_PADDING)
    except (ValueError, TypeError) as exc:
        raise ValueError("Mot de passe chiffré invalide") from exc
    return plaintext.decode("utf-8")
