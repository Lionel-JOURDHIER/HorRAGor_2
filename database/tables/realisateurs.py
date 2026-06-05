"""
models/realisateurs.py
───────────────────────
PK : director_id (INT) — identifiant natif TMDB, pas d'AUTO_INCREMENT.
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from tables.base import Base


class Realisateur(Base):
    """
    Model representing movie directors.

    Uses external IDs as primary keys and maintains a one-to-many
    relationship with the Film table.
    """

    __tablename__ = "realisateurs"

    # Primary key from external source (e.g., TMDB)
    director_id = Column(Integer, primary_key=True, autoincrement=False)

    # Director's full name (Max 35 chars)
    name = Column(String(35), nullable=False)

    # Relationship to the Film model
    # Reference by string "Film" to ensure compatibility with late binding
    films = relationship("Film", back_populates="realisateur")
