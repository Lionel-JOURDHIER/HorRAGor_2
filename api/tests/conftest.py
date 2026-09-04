# api/tests/conftest.py
import base64
import os
import sys

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Dossier contenant ce conftest : api/tests
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Dossier api
API_DIR = os.path.dirname(TESTS_DIR)

# Racine du projet : HorRAGor_2
ROOT_DIR = os.path.dirname(API_DIR)

# Ajoute la racine du projet au PYTHONPATH
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from api.auth_crypto import get_public_key_pem
from api.main import app
from database.connection import get_db
from database.tables.base import Base
from database.tables.refresh_tokens import RefreshToken
from database.tables.users import User


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    """Session SQLAlchemy sur une base SQLite en mémoire, propre par test.

    Seules les deux tables de l'authentification sont créées : le reste du
    schéma (films, embeddings) dépend de types PostgreSQL que SQLite ne sait
    pas produire, et n'a rien à faire dans un test d'authentification.

    Yields:
        Session: session ouverte sur une base vide, fermée après le test.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__, RefreshToken.__table__])
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def auth_client(db_session):
    """TestClient dont la dépendance `get_db` pointe sur la base de test.

    Args:
        db_session: session SQLite en mémoire fournie par la fixture homonyme.

    Yields:
        TestClient: client appelant l'application en mémoire, sans réseau.
    """
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def chiffrer(mot_de_passe: str) -> str:
    """Chiffre un mot de passe comme le ferait le frontend avant l'envoi.

    Les routes /auth/login et /auth/register attendent un mot de passe chiffré
    avec la clé publique exposée par l'API (RSA-OAEP/SHA-256, base64) : un mot
    de passe en clair y est refusé avec un 400.

    Args:
        mot_de_passe: Mot de passe en clair.

    Returns:
        Mot de passe chiffré, encodé en base64.
    """
    public_key = serialization.load_pem_public_key(get_public_key_pem().encode("utf-8"))
    chiffre = public_key.encrypt(
        mot_de_passe.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(chiffre).decode("utf-8")
