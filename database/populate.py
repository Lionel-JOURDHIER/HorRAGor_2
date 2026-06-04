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
    - .models (Base, Film, FilmEmbedding)

Auteur/Responsable : Lionel (Epic 1 & 2)
"""
