"""
Tests unitaires pour la validation de la structure ORM de FilmEmbedding.
"""

from models import FilmEmbedding


def test_film_embedding_structure():
    """Vérifie la définition des colonnes et de la clé primaire du modèle."""
    # 1. Vérification du nom de la table isolée
    assert FilmEmbedding.__tablename__ == "film_embeddings"

    # 2. Vérification de la présence des colonnes indispensables
    columns = FilmEmbedding.__table__.columns
    assert "tmdb_id" in columns
    assert "embedd_title" in columns
    assert "embedd_overview" in columns

    # 3. Vérification que tmdb_id est bien configuré comme clé primaire unique
    assert columns["tmdb_id"].primary_key is True


def test_film_embedding_instantiation():
    """Vérifie qu'on peut créer un objet avec des listes de vecteurs de dimension 1024."""
    # Génération de deux faux vecteurs de dimension 1024
    dummy_vector_title = [0.1] * 1024
    dummy_vector_overview = [0.5] * 1024

    # Instanciation du modèle SQLAlchemy
    instance = FilmEmbedding(
        tmdb_id=550,  # Exemple : ID de Fight Club
        embedd_title=dummy_vector_title,
        embedd_overview=dummy_vector_overview,
    )

    # Assertions pour s'assurer que les données sont correctement assignées
    assert instance.tmdb_id == 550
    assert len(instance.embedd_title) == 1024
    assert len(instance.embedd_overview) == 1024
    assert instance.embedd_title[0] == 0.1
    assert instance.embedd_overview[0] == 0.5
