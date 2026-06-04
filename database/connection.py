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
