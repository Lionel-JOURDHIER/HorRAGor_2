"""
models/scores_imdb.py
───────────────────────
PK : director_id (INT) — identifiant natif TMDB, pas d'AUTO_INCREMENT.
"""

from sqlalchemy import DECIMAL, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from tables.base import Base


class ScoreImdb(Base):
    """
    Represents the IMDb ratings and vote counts for a specific film.

    This model maintains a one-to-one relationship with the 'films' table
    via the 'tconst' foreign key.

    Attributes:
        id_score_imdb (int): Primary key, auto-incremented by the database.
        tconst (str): Foreign key referencing the film's unique identifier.
        title (str): The title of the film (redundant storage or display title).
        average_rating (Decimal): The weighted average of all individual user ratings.
        num_votes (int): Total number of votes received on IMDb.
        film (Film): Relationship object linking back to the associated Film instance.
    """

    __tablename__ = "score_imdb"

    # Primary Key managed by the DB
    id_score_imdb = Column(Integer, primary_key=True, autoincrement=True)

    # FK to Film table (tconst)
    # nullable=False: Every score record MUST be linked to a film
    # unique=True: Ensures 1:1 relationship (one score per film)
    tconst = Column(
        String(10), ForeignKey("films.imdb_id"), nullable=False, unique=True
    )

    title = Column(String(150))
    average_rating = Column(DECIMAL(3, 1))
    num_votes = Column(Integer)

    # Inverse relationship linking to the Film model
    film = relationship("Film", back_populates="score_imdb")
