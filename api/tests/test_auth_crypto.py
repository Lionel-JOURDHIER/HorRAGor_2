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


