"""
models/collections.py
──────────────────────
PK : tmdb_collection_id (INT) — identifiant natif TMDB utilisé directement
     comme clé primaire (pas d'AUTO_INCREMENT) car films.csv référence déjà
     ces valeurs.
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from tables.base import Base


class Collection(Base):
    """
    Direct SQLAlchemy model for collections.
    Focuses on database constraints over IDE type hints.
    """

    __tablename__ = "collections"

    # Direct column definition without Mapped wrappers
    tmdb_collection_id = Column(Integer, primary_key=True, autoincrement=False)
    collection_name = Column(String(60), nullable=False)

    # Standard relationship definition
    films = relationship("Film", back_populates="collection")
