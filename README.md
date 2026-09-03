# 🎬 HorRAGor

HorRAGor est une application de recommandation et d'analyse de films d'horreur. Alliant la puissance d'un moteur d'agent conversationnel intelligent (**LangGraph**, **Ollama** local) et la rigueur de filtres relationnels, elle permet aux utilisateurs d'explorer une base de données dédiée et d'obtenir des suggestions ultra-ciblées.

L'architecture est entièrement conteneurisée et pensée pour s'exécuter localement sous **WSL2 (Ubuntu)** afin de garantir un traitement souverain et sécurisé des données.

---

## 🌐 Adresses

Une fois la stack lancée (`docker compose up -d`), tout passe par Traefik sur
`localhost` — le routage se fait par chemin, pas par nom d'hôte, donc rien à
ajouter dans `/etc/hosts`. Traefik termine le TLS avec un certificat
auto-signé : le navigateur avertit à la première ouverture, à accepter
manuellement (pas de CA à installer sur le poste).

| Élément | Adresse |
|---|---|
| Frontend (Streamlit) | https://localhost |
| API IA | https://localhost/api |
| Documentation Swagger — API IA | https://localhost/api/docs |
| API Database | https://localhost/dbapi |
| Documentation Swagger — API Database | https://localhost/dbapi/docs |
| Dashboard Traefik | http://127.0.0.1:8080/dashboard/ |

La stack `monitoring/docker-compose.yml` (à lancer séparément) expose en plus :

| Élément | Adresse |
|---|---|
| Langfuse (traces LLM) | http://localhost:3000 |
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9092 |
| Uptime Kuma | http://localhost:3002 |

---

## 🛠️ Stack Technique

* **Front-End** : Streamlit (Python)
* **API IA** : FastAPI & Pydantic (agent LangGraph, streaming SSE)
* **API Database** : FastAPI dédiée à l'accès aux données (aucune logique IA)
* **Orchestration IA** : LangGraph & LangChain (modèle local via Ollama, exécuté sur l'hôte)
* **Base de Données** : Supabase (PostgreSQL) exploité via **SQLAlchemy**
* **Recherche Sémantique** : Index vectoriel **FAISS** chargé en RAM, persisté dans un volume Docker
* **Observabilité** : Prometheus (métriques), Langfuse (traces LLM)
* **Environnement** : Docker Compose, WSL2 (Ubuntu)

---

## 📂 Architecture du Projet

Le projet est découpé en composants autonomes (KISS/DRY), chacun avec son propre `pyproject.toml`/`uv.lock` :

```text
HORRAGOR_2/
├── agents/                # Moteur de l'agent intelligent (LangGraph)
│   ├── tools/             # Outils de l'agent (SQL, FAISS, Wikipédia)
│   ├── graph.py           # Assemblage et orchestration du StateGraph
│   ├── router.py          # Routage RAG / Wikipedia / narrateur
│   ├── nodes_rag.py        # Nœud de récupération vectorielle + SQL
│   ├── nodes_wikipedia.py  # Nœud de récupération Wikipédia
│   ├── nodes_narrateur.py  # Nœud de génération narrative
│   ├── state.py            # Structure de données circulante (AgentState)
│   └── prompts.py          # Centralisation de l'ingénierie des invites
├── api/                    # API IA (FastAPI) — orchestration de l'agent uniquement
│   ├── modules/
│   │   ├── chat_service.py      # Exécution du graphe LangGraph, streaming
│   │   └── database_client.py   # Client HTTP vers l'API Database
│   ├── monitoring/          # Intégration Langfuse
│   ├── routes.py            # Endpoints /health, /chat/response_stream, /wikipedia
│   ├── routes_monitoring.py # Endpoints /monitoring/metrics, /monitoring/traces
│   └── main.py               # Point d'entrée du serveur (charge l'index FAISS)
├── database/                # API Database (FastAPI) — accès aux données uniquement
│   ├── tables/               # Tables SQLAlchemy (Film, Genre, Réalisateur, Scores...)
│   ├── connection.py          # Initialisation de la session de base de données
│   ├── faiss_service.py       # Gestion globale de l'index vectoriel en RAM
│   ├── models.py               # Modèles SQLAlchemy
│   ├── queries.py               # Requêtes métier (jointures, agrégats, filtres)
│   ├── populate.py              # Script d'initialisation et d'ingestion des données
│   ├── routes_db.py             # Endpoints /db/health, /db/list_real, /db/film/{id}...
│   └── main.py                   # Point d'entrée du serveur
├── frontend/                # Interface utilisateur (Streamlit)
│   ├── components/           # Composants d'affichage réutilisables
│   ├── utils/                 # Client API
│   └── app.py                  # Point d'entrée IHM avec le formulaire de préférences
├── monitoring/               # Configuration Prometheus / Grafana
├── shared/                    # Schémas Pydantic partagés entre les sous-projets
├── docker-compose.yml         # Orchestration multi-conteneurs locale (api, database_api, frontend)
├── .gitignore                  # Protections des index, variables d'environnement et caches
└── .env.example                # Modèle de configuration des variables d'environnement
```

---

## 🚦 Endpoints

L'API IA et l'API Database sont deux services FastAPI distincts.

### API IA (port `8000`, `api/routes.py`)

- `GET /health` : état de santé de l'API IA.
- `POST /chat/response_stream` : exécute l'agent LangGraph et streame en SSE les étapes intermédiaires (`step`) puis la réponse finale validée (`final`, `ChatResponse` avec film/recommandations).
- `GET /wikipedia/{tmdb_id}` : extrait le synopsis Wikipédia d'un film à partir de son ID TMDB.
- `GET /monitoring/metrics`, `GET /monitoring/traces` : métriques et traces Langfuse (`api/routes_monitoring.py`).

### API Database (port `8001`, `database/routes_db.py`, préfixe `/db`)

- `GET /db/health` : état de santé de l'accès aux données.
- `GET /db/list_real` : liste des réalisateurs.
- `GET /db/list_genre` : liste des genres.
- `GET /db/film/{tmdb_id}` : détail complet d'un film par ID TMDB.
- `POST /db/filter_films` : filtre les films par critères métier, retourne une liste d'IDs TMDB.
- `POST /db/films/details` : détails de plusieurs films à partir d'une liste d'IDs.
- `POST /db/films/short` : version compacte de plusieurs films à partir d'une liste d'IDs (utilisé après une recherche FAISS).

---

## 🎛️ Formulaire de Préférences (IHM)

L'interface conçue pour les utilisateurs permet d'ajuster les préférences en temps réel grâce à un formulaire physique strict :

- Filtres textuels/catégoriels : Sélection du réalisateur, genres à conserver, genres non souhaités.
- Filtres numériques (Sliders) :
  - Année de sortie : de 1900 à 2026.
  - Score TMDB : de 0 à 10.
  - Durée du film : de 1 à 685 minutes.

---

## 🔑 Configuration & Sécurité

La connexion s'appuie sur des variables d'environnement chargées via un fichier `.env` (voir `.env.example`).

### Pooler Supabase & Résilience

Pour absorber les requêtes en parallèle (API Database + scripts d'indexation) et éviter la saturation du réseau, le moteur configure un pool de connexions optimisé :
* **`pool_size=5`** & **`max_overflow=10`** : allocation dynamique des connexions.
* **`pool_pre_ping=True`** : test systématique de la viabilité de la connexion avant exécution (indispensable pour prévenir les déconnexions intempestives du pooler Supabase).

### Première connexion à Langfuse (traces LLM)

Langfuse (`docker compose -f monitoring/docker-compose.yml up -d`) est initialisé au premier démarrage avec l'utilisateur défini dans `monitoring/.env` (`LANGFUSE_INIT_USER_EMAIL` / `LANGFUSE_INIT_USER_PASSWORD`), mais **sans clé API** tant que `LANGFUSE_INIT_PROJECT_PUBLIC_KEY` / `LANGFUSE_INIT_PROJECT_SECRET_KEY` ne sont pas renseignées.

1. Se connecter sur `http://localhost:3000` avec les identifiants `LANGFUSE_INIT_USER_*` de `monitoring/.env`.
2. Dans le projet, **Settings → API Keys → Create new API key** : la clé secrète n'est affichée qu'une seule fois à la création, à copier immédiatement.
3. Reporter la paire `public key` / `secret key` dans le `.env` racine (`LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`), consommées par `api/monitoring/langfuse_client.py`.
4. Recréer le conteneur `api` pour que la nouvelle valeur soit prise en compte — `docker compose restart api` ne relit **pas** `env_file` :
   ```bash
   docker compose up -d --force-recreate api
   ```

---

## 🔍 Logique Métier & Requêtes (`database/queries.py`)

Le fichier `database/queries.py` sert de pont unique entre les modèles de tables SQLAlchemy et les schémas d'API Pydantic partagés (`shared/schemas.py`). Il intègre les fonctionnalités clés suivantes :

1. **Jointure multi-tables (format détaillé)** : `get_film_details_by_id` centralise l'extraction de l'entité `Film` en y greffant l'ensemble de ses métadonnées critiques (`ScoresTmdb`, `ScoresImdb`, `ScoresRt`), son `Realisateur` et sa `Collection` via des jointures externes (`outerjoin`).
2. **Résolution many-to-many** : extrait la liste des genres associés à un film en passant par la table pivot `FilmGenre`.
3. **Calcul de score agrégé** : calcule dynamiquement une note critique globale harmonisée sur une base 100 en ignorant strictement les valeurs `None` afin de ne pas fausser les statistiques.
4. **Extraction en lot (format court)** : `get_films_short_by_ids`/`get_films_details_by_ids` permettent, à partir d'une liste d'identifiants (retournée par **FAISS**), d'extraire en une seule passe (`.in_()`) les métadonnées des films, évitant le piège de performance des requêtes répétitives (N+1 query).
5. **Filtrage métier** : `get_filtered_ids` applique les critères du formulaire de préférences (réalisateur, genres inclus/exclus, année, score, durée) et retourne les IDs TMDB correspondants.
