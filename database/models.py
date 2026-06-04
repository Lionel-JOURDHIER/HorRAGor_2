"""database/models.py
Module de définition des modèles de données (ORM) pour le projet HorRAGor.

Ce fichier utilise SQLAlchemy 2.0 pour mapper les tables PostgreSQL hébergées
sur Supabase. Il fait le pont entre les données textuelles pures et les structures
vectorielles nécessaires à l'indexation.

Tables mappées :
    - Film : Reflet de la table de production existante (en lecture seule pour ce module),
             contenant les métadonnées des films (titre, réalisateur, synopsis, durée, etc.).
    - FilmEmbedding : Nouvelle table dédiée au stockage persistant des vecteurs
                      d'embeddings (dimension 1024) générés localement par le
                      modèle `qwen3-embedding:0.6b`.

Dépendances principales :
    - sqlalchemy.orm (DeclarativeBase, Mapped, mapped_column)
    - pgvector.sqlalchemy (Vector)

Auteur/Responsable : Lionel (Epic 1 & 2)
"""
