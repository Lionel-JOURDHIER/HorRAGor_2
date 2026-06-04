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
