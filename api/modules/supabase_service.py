"""api/modules/supabase_service.py

Service layer responsible for all interactions with the Supabase database.

This module centralizes database access logic and provides reusable methods
for querying movie data, directors, genres, ratings, and vector search results.

Responsibilities:
    - Initialize and manage the Supabase client.
    - Execute database queries.
    - Retrieve movie information.
    - Retrieve directors and genres.
    - Support recommendation and similarity search features.
    - Isolate database logic from API routes.

Notes:
    - API routes must not access Supabase directly.
    - All database operations should be implemented through this service.
    - This module will later be used by LangGraph tools and FastAPI endpoints.

Dependencies:
    - supabase
    - python-dotenv
    - os

Author: Hanna
Project: HorRAGor
"""
import os
from os import getenv

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

class SupabaseService:
    """ Service responsible for communication with the Supabase database."""

    def __init__(self) -> None:
        """ Initialize the Supabase client using environment variables."""

        self.url = getenv("SUPABASE_URL")
        self.key = getenv("SUPABASE_KEY")

        self.client: Client = create_client(
            self.url,
            self.key
        )

    def check_connection(self) -> bool:
        """ Verify that the database is reachable.

        Returns:
            bool:
                True if the connection succeeds, otherwise False.
        """

        try:
            self.client.table("FILMS").select(
                "tmdb_id"
            ).limit(1).execute()

            return True

        except Exception:
            return False
        
    def get_film_by_id( self, tmdb_id: int):
        """ Retrieve a movie by its TMDB identifier.

        Args:
            tmdb_id (int):
                Unique TMDB movie identifier.

        Returns:
            dict:
                Movie information from the database.
        """

        pass

    def get_directors(self):
        """ Retrieve all directors available in the database.

        Returns:
            list[str]:
                List of director names.
        """

        pass

    def get_genres(self):
        """ Retrieve all genres available in the database.

        Returns:
            list[str]:
                List of genre names.
        """

        pass

    def search_similar_movies( self, embedding: list[float], top_k: int = 5):
        """ Perform a semantic similarity search using PGVector.

        Args:
            embedding (list[float]):
                Query embedding vector.

            top_k (int):
                Number of movies to return.

        Returns:
            list[dict]:
                Most similar movies.
        """

        pass


supabase_service = SupabaseService()
