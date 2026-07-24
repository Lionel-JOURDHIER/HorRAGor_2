"""database/populate.py
Script d'extraction, de vectorisation locale et d'alimentation (Populate).

Ce module s'exécute de manière autonome ou planifiée pour synchroniser la nouvelle
table 'film_embeddings' sur Supabase à partir des données de la table 'films'.
Il garantit une isolation complète et une sécurité totale vis-à-vis des données existantes.

Processus séquentiel :
    1. Initialisation sécurisée : Crée la table 'film_embeddings' si elle n'existe pas
       (sans altérer ni modifier la table 'films').
    2. Lecture seule : Récupère les identifiants, titres et synopsis depuis Supabase.
    3. Déduplication (DRY) : Identifie et ignore les films déjà vectorisés lors d'une
       session précédente.
    4. Inférence locale et souveraine : Appelle l'instance locale Ollama pour générer
       les vecteurs sémantiques (dimension 1024 via qwen3-embedding:0.6b).
    5. Upload : Injecte les vecteurs par lots (batchs) directement dans le Cloud Supabase.

Dépendances principales :
    - sqlalchemy.orm (Session)
    - langchain_ollama (OllamaEmbeddings)
    - .connection (engine, SessionLocal)
    - .models (Base, FilmEmbedding)

Auteur/Responsable : Lionel (Epic 1 & 2)
"""

import os

from dotenv import load_dotenv
from shared.embeddings import OLLAMA_CLIENT_EMBEDD
from sqlalchemy import text

from database.connection import engine, get_db
from database.models import Base, FilmEmbedding

load_dotenv()

_OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
# OLLAMA_CLIENT_EMBEDD = OllamaEmbeddings(
#     model="qwen3-embedding:0.6b", base_url=_OLLAMA_URL
# )


def fetch_source_films(session) -> list:
    """Extrait l'ID, le titre et l'overview de la table existante 'films'."""
    query = text("SELECT tmdb_id, title, overview FROM films")
    return session.execute(query).fetchall()


def fetch_already_vectorized_ids(session) -> set[int]:
    """Récupère les IDs déjà présents dans la table d'embeddings pour la déduplication."""
    query = text("SELECT tmdb_id FROM film_embeddings")
    result = session.execute(query).fetchall()
    return {row.tmdb_id for row in result}


def generate_local_embedding(text_content: str) -> list[float]:
    """
    Génère un vecteur de dimension 1024 via l'instance locale Ollama.

    Dépendance : qwen3-embedding:0.6b s'exécutant sur le réseau local/WSL.
    """
    # Gestion des chaînes vides ou None pour éviter de faire crasher Ollama
    if not text_content or not text_content.strip():
        return [0.0] * 1024

    # --- LE VRAI TRAVAIL COMMENCE ICI ---
    # Initialisation du client Ollama avec ton modèle souverain (dim 1024 d'après tes specs)
    ollama_client = OLLAMA_CLIENT_EMBEDD

    # Appel de l'inférence locale
    return ollama_client.embed_query(text_content)


def run_pipeline():
    """Pilote le flux complet conforme au processus séquentiel documenté."""
    print("🛰️ Étape 1 : Initialisation sécurisée de l'extension RAG sur Supabase...")
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        Base.metadata.create_all(conn, tables=[FilmEmbedding.__table__])

    # Utilisation propre du générateur existant via un Context Manager
    with next(get_db()) as session:
        try:
            # Étape 2 : Lecture seule
            print("📥 Étape 2 : Extraction des données sources depuis 'films'...")
            records = fetch_source_films(session)

            # Étape 3 : Déduplication
            print(
                "🔍 Étape 3 : Vérification des enregistrements existants (Déduplication)..."
            )
            existing_ids = fetch_already_vectorized_ids(session)

            films_to_process = [r for r in records if r.tmdb_id not in existing_ids]
            print(
                f"-> {len(records)} films trouvés au total, {len(films_to_process)} à vectoriser."
            )

            # Étape 4 & 5 : Inférence locale et Injection par lots (Batch de 50)
            if films_to_process:
                total_films = len(films_to_process)
                BATCH_SIZE = 50
                print(
                    f"🧠 Étape 4 & 5 : Inférence locale Ollama et injection par lots de {BATCH_SIZE}..."
                )

                current_batch = []

                for index, record in enumerate(films_to_process, start=1):
                    # Affichage de l'avancement global en temps réel
                    print(
                        f"   ⏳ [Avancement : {index}/{total_films}] Vectorisation de : '{record.title}'...",
                        end="\r",
                        flush=True,
                    )

                    try:
                        v_title = generate_local_embedding(record.title)
                        v_overview = generate_local_embedding(record.overview)

                        entry = FilmEmbedding(
                            tmdb_id=record.tmdb_id,
                            embedd_title=v_title,
                            embedd_overview=v_overview,
                        )
                        current_batch.append(entry)

                    except Exception as e:
                        # Si l'inférence d'un film plante (Ollama crash par exemple), on sauvegarde au moins le lot actuel avant de lever l'erreur
                        if current_batch:
                            for item in current_batch:
                                session.merge(item)
                            session.commit()
                        print(
                            f"\n❌ Erreur d'inférence sur le film '{record.title}': {e}"
                        )
                        raise e

                    # Dès qu'on atteint la taille du lot (50) ou qu'on arrive au tout dernier film
                    if len(current_batch) == BATCH_SIZE or index == total_films:
                        print(
                            f"\n   📤 [Batch] Injection et sauvegarde de {len(current_batch)} films sur Supabase..."
                        )

                        for item in current_batch:
                            session.merge(item)

                        session.commit()  # Sauvegarde définitive dans le Cloud
                        current_batch = []  # On vide le tampon local pour le prochain lot

                print(
                    "\n🎉 Synchronisation avec le Cloud Supabase réussie à 100 % ! All checkpoints saved."
                )

        except Exception as e:
            session.rollback()
            print(f"❌ Échec critique du pipeline : {e}")
            raise e


if __name__ == "__main__":
    run_pipeline()
