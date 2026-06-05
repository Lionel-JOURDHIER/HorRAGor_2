"""
Modèles ORM SQLAlchemy pour l'extension RAG HorRAGor.
"""

from pgvector.sqlalchemy import Vector  # Extension pgvector native de Supabase
from sqlalchemy import Column, Integer
from sqlalchemy.orm import DeclarativeBase


# 0. Classe de base déclarative partagée par tous les modèles ORM (ex: Film, FilmEmbedding)
class Base(DeclarativeBase):
    """Classe de base declarative SQLAlchemy 2.0 pour HorRAGor."""

    pass


class FilmEmbedding(Base):
    """
    Table d'extension RAG autonome contenant uniquement les identifiants
    et les vecteurs associés de dimension 1024.
    """

    __tablename__ = "film_embeddings"

    # Clé primaire alignée sur la table d'origine
    tmdb_id = Column(Integer, primary_key=True, autoincrement=False)

    # Tes deux colonnes de vecteurs distinctes (dimension 1024)
    embedd_title = Column(Vector(1024), nullable=False)
    embedd_overview = Column(Vector(1024), nullable=False)
