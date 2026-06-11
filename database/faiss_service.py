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

import json
import os
from pathlib import Path

import faiss
import numpy as np
from sqlalchemy.orm import Session

from database.models import FilmEmbedding

# --- CONFIGURATION DES CHEMINS ABSOLUS (DRY) ---
BASE_DIR = Path(__file__).resolve().parent.parent  # Racine du projet HorRAGor
FAISS_DIR = BASE_DIR / "data" / "faiss_index"
INDEX_PATH = str(FAISS_DIR / "faiss.index")
MAPPING_PATH = str(FAISS_DIR / "mapping.json")


class FaissService:
    def __init__(self, dimension: int = 1024):
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.id_mapping = {}

    def build_index(self, session: Session):
        """Charge tous les vecteurs depuis Supabase vers FAISS."""
        embeddings = session.query(FilmEmbedding).all()
        vectors = []
        for i, emb in enumerate(embeddings):
            vector = np.array(emb.embedd_title, dtype="float32")
            vectors.append(vector)
            self.id_mapping[i] = emb.tmdb_id

        if vectors:
            data = np.array(vectors).astype("float32")
            self.index.add(data)
            print(f"✅ Index FAISS construit avec {len(vectors)} films.")

    def save_index(self, index_path: str, mapping_path: str) -> None:
        """
        Persiste l'index FAISS et le mapping sur disque.

        Args:
            index_path:   Chemin du fichier .index (format binaire FAISS).
            mapping_path: Chemin du fichier .json (mapping faiss_id → tmdb_id).
        """
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        faiss.write_index(self.index, index_path)
        with open(mapping_path, "w") as f:
            json.dump(self.id_mapping, f)
        print(f"💾 Index FAISS sauvegardé : {self.index.ntotal} films → {index_path}")

    def load_index(self, index_path: str, mapping_path: str) -> bool:
        """
        Charge l'index FAISS et le mapping depuis le disque.

        Returns:
            True si le chargement a réussi, False si les fichiers sont absents.
        """
        if not os.path.exists(index_path) or not os.path.exists(mapping_path):
            print("ℹ️  Aucun index persisté trouvé — construction requise.")
            return False

        self.index = faiss.read_index(index_path)
        with open(mapping_path, "r") as f:
            raw = json.load(f)
            # JSON sérialise les clés en string — on les reconvertit en int
            self.id_mapping = {int(k): v for k, v in raw.items()}

        print(f"✅ Index FAISS chargé depuis disque : {self.index.ntotal} films.")
        return True

    def search(self, query_vector: list, k: int = 1):
        """
        Recherche dans l'index FAISS.
        Retourne un tuple (ids, distances) au lieu de juste les ids.
        """
        import numpy as np

        xq = np.array([query_vector]).astype("float32")

        # D = distances, I = indices FAISS
        D, I = self.index.search(xq, k)

        results = []
        for distance, faiss_id in zip(D[0], I[0]):
            if faiss_id in self.id_mapping:
                tmdb_id = self.id_mapping[faiss_id]
                results.append((tmdb_id, float(distance)))

        return results

    def load_or_build(self, session: Session) -> None:
        """Tente de charger l'index depuis le disque, sinon le construit depuis SQL."""
        # Utilise les chemins absolus centralisés du module
        if self.load_index(INDEX_PATH, MAPPING_PATH):
            return

        print("ℹ️ Index introuvable sur le disque. Construction depuis Supabase...")
        self.build_index(session)

        print("💾 Persistance automatique de l'index sur le disque...")
        self.save_index(INDEX_PATH, MAPPING_PATH)

    def get_vector_by_id(self, movie_id: int) -> list[float] | None:
        """
        Récupère le vecteur d'un film à partir de son identifiant TMDB.
        Cherche directement dans l'index FAISS via le mapping inverse en RAM.
        """
        if not self.id_mapping:
            print("⚠️ Le mapping FAISS est vide. L'index a-t-il été build ?")
            return None

        # On cherche l'ID FAISS (l'index de la ligne) correspondant au movie_id (TMDB)
        # Si ton mapping est inversé (ex: {faiss_id: movie_id}), on le parcourt :
        for faiss_id, tmdb_id in self.id_mapping.items():
            if tmdb_id == movie_id:
                # Récupération directe du vecteur dans la matrice de l'index FAISS
                return self.index.reconstruct(faiss_id).tolist()

        print(f"🎬 ID TMDB {movie_id} introuvable dans l'index FAISS local.")
        return None


faiss_global_service = FaissService(dimension=1024)

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
