"""database/connection.py
Module de configuration de la connexion à la base de données distante Supabase.

Ce fichier gère l'initialisation du moteur de base de données (Engine) et la
création de la fabrique de sessions (sessionmaker) via SQLAlchemy 2.0. Il s'assure
que les connexions vers le cloud Supabase sont optimisées, sécurisées et recyclées
correctement pour éviter les fuites de ressources.

Fonctionnalités principales :
    - Chargement des variables d'environnement (URI de connexion Supabase via .env).
    - Configuration du pool de connexions (pool_size, max_overflow) pour absorber
      les requêtes en parallèle de l'API FastAPI et du script d'indexation.
    - Mise à disposition de 'SessionLocal' pour l'exécution des requêtes ORM.

Variables d'environnement requises :
    - SUPABASE_DATABASE_URL : Chaîne de connexion PostgreSQL directe ou via pooler.

Dépendances principales :
    - sqlalchemy (create_engine)
    - sqlalchemy.orm (sessionmaker)
    - dotenv (load_dotenv)

Auteur/Responsable : Lionel (Epic 1 & 2)
"""

import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()


# 1. Construction dynamique de l'URL de connexion à partir du .env
# On cherche d'abord les variables Supabase, sinon on se rabat sur le Postgres local
DB_USER = os.getenv("SUPABASE_USER")
DB_PASSWORD = os.getenv("SUPABASE_PASSWORD", "<MOT_DE_PASSE>")
DB_HOST = os.getenv("SUPABASE_HOST")
DB_PORT = os.getenv("SUPABASE_PORT")
DB_NAME = os.getenv("SUPABASE_DB")

# Assemblage de l'URL au format PostgreSQL standard
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Sécurité : Vérification sommaire que le mot de passe n'est pas resté au format exemple
if "<MOT_DE_PASSE>" in DATABASE_URL:
    raise ValueError(
        "❌ Erreur : Le mot de passe par défaut '<MOT_DE_PASSE>' est détecté.\n"
        "Veuillez mettre à jour votre fichier .env avec vos vrais identifiants."
    )  # pragma: no cover

# 2. Création du moteur SQLAlchemy
# pool_pre_ping=True teste la connexion avant usage (indispensable avec le pooler Supabase)
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)

# 3. Configuration de la fabrique de sessions locales
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Générateur (Context Manager) de session de base de données.

    Ouvre une session SQLAlchemy et garantit sa fermeture automatique après
    exécution, évitant ainsi la saturation du pooler Supabase.

    Yields:
        Session: Une instance de session SQLAlchemy active.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
