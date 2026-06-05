# 🗄️ HorRAGor - Module Database & Vector Index

Ce sous-dossier regroupe toute la logique de persistance des données relationnelles, la génération et le stockage des embeddings sémantiques, ainsi que la gestion en mémoire (RAM) de l'index vectoriel **FAISS**.

---

## 🏗️ Architecture du Module

```text
database/
├── tests/              # Tests unitaires et d'intégration
│   ├── conftest.py     # Injection automatique du PYTHONPATH pour les tests
│   └── test_connection.py # Validation du ping Supabase / Postgres
├── connection.py       # Configuration du moteur SQLAlchemy 2.0 et pool de sessions
├── faiss_service.py    # Service de manipulation de l'index FAISS chargé en RAM
├── models.py           # Modèles ORM (Film existant & FilmEmbedding pgvector)
├── populate.py         # Script d'ingestion et de vectorisation initiale
├── pyproject.toml      # Dépendances isolées du module (gérées via uv)
└── uv.lock             # Fichier de verrouillage des versions exactes de Python
```

## 🛢️ Modèles de Données (ORM)
Le fichier models.py fait cohabiter la table de production existante et notre extension RAG :

1. Film : Table de production existante (mappée via les types natifs SQLAlchemy). Elle centralise les métadonnées (titres, réalisateurs via director_id, durées, etc.).

2. FilmEmbedding : Nouvelle table dédiée. Elle stocke les morceaux de texte (content_chunk) et leur représentation vectorielle (embedding) de dimension 1024 générée localement par le modèle d'embedding via Ollama. Elle est liée à la table principale par la clé films.tmdb_id (en CASCADE on delete).


## 🚀 Configuration & Variables d'Environnement
Le fichier connection.py assemble dynamiquement l'URL de connexion. Créez un fichier .env dans ce dossier inspiré de .env.example :

```toml
# Configuration locale (Docker / Dev)
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=horror_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Configuration Production (Supabase via Pooler)
SUPABASE_USER=postgres.[votre_projet]
SUPABASE_PASSWORD=[votre_mot_de_passe]
SUPABASE_HOST=db.[votre_projet].supabase.co # Ou l'URL du pooler session
SUPABASE_PORT=6543
SUPABASE_DB=postgres
```
💡 Sécurité & Robustesse : Le moteur intègre l'option pool_pre_ping=True pour éviter les déconnexions intempestives du pooler Supabase, 
et lève une alerte si les balises d'exemple <MOT_DE_PASSE> n'ont pas été modifiées.

## 🧪 Validation de la Plomberie (Tests)
Les tests sont gérés proprement grâce à uv et pytest. Un fichier conftest.py centralise la configuration du path pour éviter toute redondance.

Pour lancer le test de connexion à la base de données :
```bash
# Depuis le dossier 'database'
uv run pytest -s
```

