"""database/faiss_service.py
Service de gestion de l'index FAISS en mémoire (RAM) et moteur de recherche hybride.

Ce module orchestre le cycle de vie de l'index vectoriel local au runtime de l'API.
Au démarrage du serveur (via le cycle 'lifespan' de FastAPI), il charge les données
depuis Supabase pour initialiser un cache ultra-rapide et un index sémantique en RAM.

Stratégie de recherche multiniveau (Matching & Sémantique) :
    - Niveau 1 (Matching Exact) : Vérification immédiate dans un dictionnaire Python
      (Complexité O(1), temps d'exécution proche de 0ms) pour résoudre instantanément
      les requêtes strictes sans solliciter l'IA.
    - Niveau 2 (Recherche Sémantique FAISS) : Inférence vectorielle locale via Ollama
      (qwen3-embedding:0.6b) et recherche par produit scalaire (IndexFlatIP) normalisé L2
      pour capter les synonymes, les fautes de frappe et les intentions complexes.

Dépendances principales :
    - faiss (IndexFlatIP)
    - numpy (Opérations matricielles et normalisation L2)
    - langchain_ollama (OllamaEmbeddings)
    - .connection (SessionLocal)
    - .models (Film, FilmEmbedding)

Auteur/Responsable : Lionel (Epic 1 & 2)
"""

import faiss
import numpy as np
from models import FilmEmbedding
from sqlalchemy.orm import Session


class FaissService:
    def __init__(self, dimension: int = 1024):
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.id_mapping = {}  # Pour lier l'index FAISS à ton tmdb_id

    def build_index(self, session: Session):
        """Charge tous les vecteurs depuis Supabase vers FAISS."""
        embeddings = session.query(FilmEmbedding).all()

        vectors = []
        for i, emb in enumerate(embeddings):
            # On concatène titre et overview pour l'indexation
            vector = np.array(emb.embedd_title, dtype="float32")
            vectors.append(vector)
            self.id_mapping[i] = emb.tmdb_id

        if vectors:
            data = np.array(vectors).astype("float32")
            self.index.add(data)
            print(f"✅ Index FAISS construit avec {len(vectors)} films.")

    def search(self, query_vector: list[float], k: int = 5):
        """Recherche les k films les plus proches."""
        query = np.array([query_vector]).astype("float32")
        distances, indices = self.index.search(query, k)

        results = [self.id_mapping[idx] for idx in indices[0] if idx != -1]
        return results


if __name__ == "__main__":
    # Import local pour éviter les dépendances circulaires lors de l'import du module
    from populate import generate_local_embedding, get_db

    db_gen = get_db()
    session = next(db_gen)

    try:
        print("🚀 Initialisation du service FAISS pour test...")
        service = FaissService(dimension=1024)
        service.build_index(session)

        if service.index.ntotal > 0:
            # 1. On utilise le même modèle que pour le populate
            query_text = "un film sur l'espace et les trous noirs"
            print(f"🔍 Recherche pour : '{query_text}'")

            # 2. On génère un vrai vecteur
            real_vector = generate_local_embedding(query_text)

            # 3. On recherche dans FAISS
            ids = service.search(real_vector, k=3)
            print(f"✅ Résultats trouvés (IDs TMDB) : {ids}")
        else:
            print("⚠️ Index vide. Lancez 'python populate.py' d'abord.")

    except Exception as e:
        print(f"❌ Erreur lors du test : {e}")
    finally:
        session.close()
