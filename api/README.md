# 🤖 HorRAGor - Module API (agent conversationnel)

Ce sous-dossier expose l'API REST FastAPI qui sert le graphe LangGraph
(routage RAG / Wikipedia / narrateur) au frontend Streamlit : chat en
streaming, recherche de films, authentification, monitoring.

---

## 🏗️ Architecture du module

```text
api/
├── tests/                   # Tests unitaires et d'intégration (TestClient)
├── modules/                 # Services applicatifs (chat_service, database_client...)
├── monitoring/               # Instrumentation Langfuse / Prometheus
├── main.py                  # Point d'entrée FastAPI, cycle de vie (lifespan)
├── routes.py                 # Endpoints films, recherche, chat
├── routes_monitoring.py      # Endpoints de supervision
├── auth_routes.py            # Endpoints d'authentification (/auth/*)
├── auth_utils.py             # Création/validation des tokens JWT
├── auth_config.py            # Configuration des secrets d'authentification
├── schemas.py                 # Schémas Pydantic propres à l'authentification
├── pyproject.toml            # Dépendances isolées du module (gérées via uv)
└── uv.lock                    # Fichier de verrouillage des versions exactes
```

Les schémas partagés avec `agents/` et `database/` (films, filtres, état de
l'agent) vivent dans [shared/schemas.py](../shared/schemas.py), pas ici.

## 🚀 Démarrage

Le service tourne derrière Traefik (`docker compose up`) sous `/api` — voir
le [CLAUDE.md](../CLAUDE.md) racine pour les commandes complètes et les
variables d'environnement requises (`FAISS_INDEX_PATH`, `OLLAMA_BASE_URL`,
`JWT_SECRET_KEY`...).

## 🧪 Tests

```bash
# Depuis le dossier 'api'
uv run pytest
```
