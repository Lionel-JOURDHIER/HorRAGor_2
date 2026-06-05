"""
models/scores_imdb.py
───────────────────────
PK : director_id (INT) — identifiant natif TMDB, pas d'AUTO_INCREMENT.
"""

from sqlalchemy import DECIMAL, Column, ForeignKey, Integer
from sqlalchemy.orm import relationship
from tables.base import Base


class ScoreTmdb(Base):
    """
    Stores metrics and popularity data from The Movie Database (TMDB).

    This model links dynamic performance metrics (popularity) and user
    ratings from TMDB to the main film records.

    Attributes:
        id_score_tmdb (int): Internal primary key.
        tmdb_id (int): Foreign key linking to the TMDB identifier in the films table.
        vote_average (Decimal): Average user rating on a scale of 10.
        vote_count (int): Total number of user ratings.
        popularity (Decimal): TMDB popularity score (high precision).
        film (Film): Relationship back to the associated Film entity.
    """

    __tablename__ = "score_tmdb"

    # Auto-incremented Primary Key
    id_score_tmdb = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign Key to films.tmdb_id
    # nullable=False: Every score must reference a film
    # unique=True: Ensures a strict 1:1 relationship
    tmdb_id = Column(Integer, ForeignKey("films.tmdb_id"), nullable=False, unique=True)

    # User ratings stats
    vote_average = Column(DECIMAL(3, 1))
    vote_count = Column(Integer)

    # High precision (10,4) to match TMDB API's popularity metric
    popularity = Column(DECIMAL(10, 4))

    # Inverse relationship with the Film model
    film = relationship("Film", back_populates="score_tmdb")
