# TODO HorRAGor

Suivi des manquements identifiés par rapport au cahier des charges
(`HorRAGor BOT Partie 3.pdf`) et de bugs relevés par relecture de code.
Mis à jour au fil des sessions.

## 🐛 Bugs confirmés — câblage frontend / backend

- [ ] **Cartes de films non affichées quand un seul film est trouvé.**
  L'API renvoie `film` (FilmDetail) quand `len(movies) == 1` et
  `recommendations` (liste) quand il y en a plusieurs
  ([api/routes.py:200-224](api/routes.py:200)). Le frontend ne lit jamais
  `event.get("film")` ([frontend/app.py:509-510](frontend/app.py:509)) : dans
  ce cas `films = []` et l'UI affiche « Aucun film ne correspond à vos
  critères » alors que l'agent a bien trouvé le film.
  → Corriger `app.py` pour intégrer `event.get("film")` dans les films à
  afficher.

- [ ] **Affiches (posters) jamais correctement affichées.**
  `poster_url=f"{film.poster_path}"` dans
  [database/queries.py:119](database/queries.py:119) et
  [:212](database/queries.py:212) réutilise le chemin relatif TMDB
  (`/xxx.jpg`) sans préfixer `https://image.tmdb.org/t/p/w500`. L'`<img>`
  généré dans [frontend/components/components.py:95](frontend/components/components.py:95)
  pointe vers une ressource inexistante sur le domaine Streamlit.
  → Préfixer `poster_url` (et vérifier `backdrop_url`) avec l'URL de base du
  CDN TMDB.

- [ ] **Sidebar des filtres (réalisateur, genres) toujours cassée.**
  [frontend/components/components.py:364](frontend/components/components.py:364)
  et [:396](frontend/components/components.py:396) appellent
  `{API_URL}/list_real` et `{API_URL}/list_genre` sur l'**API IA** (port
  8000). Ces routes n'existent que sur l'**API Database** (port 8001, préfixe
  `/db/`, voir [database/routes_db.py](database/routes_db.py)). Résultat :
  404 systématique, le sélecteur reste bloqué sur « Tous ».
  → Soit exposer un proxy `/list_real` et `/list_genre` sur l'API IA, soit
  donner au frontend une deuxième variable d'env (`DATABASE_API_URL`) pour
  cibler directement l'API Database.

- [ ] **Fonctions mortes et cassées dans `api_client.py`** (non appelées par
  `app.py` aujourd'hui, mais cassées si utilisées un jour, et couvertes par
  des tests d'intégration qui échoueraient si `--run-integration` était
  activé) :
  - `get_film_by_id`, `get_realisateurs`, `get_genres` → visent l'API IA au
    lieu de l'API Database (même bug que la sidebar).
  - `send_chat_query` (version non-streaming) → appelle `POST /chat/response`,
    entièrement commenté côté serveur ([api/routes.py:65-118](api/routes.py:65))
    → 404 garanti.
  → Décider : les corriger et les câbler, ou les supprimer avec leurs tests.

## 🟠 Robustesse au démarrage

- [ ] **Pas de reconstruction automatique de l'index FAISS.**
  [api/main.py](api/main.py:51) appelle uniquement `load_index()` au
  démarrage et lève `RuntimeError` si les fichiers sont absents.
  `build_index()` est du code mort, commenté dans
  [database/faiss_service.py:49](database/faiss_service.py:49). Sur un clone
  neuf sans `faiss_data/` pré-généré, le conteneur `api` ne démarre pas —
  contrairement à ce que documente le QUICKSTART ("déclenche la première
  synchronisation... depuis Supabase").
  → Soit documenter l'étape manuelle (`uv run database/populate.py` avant le
  premier `docker compose up`), soit ré-activer `build_index()` au démarrage
  si l'index est absent.

## 🔴 Sécurité (Épilogue MLOps du cahier des charges)

- [ ] Authentification par **Refresh Tokens** entre le frontend et l'API IA —
  aucune trace de code, `pyjwt` présent uniquement comme dépendance
  transitive dans [api/uv.lock](api/uv.lock).
- [ ] Communication **chiffrée** frontend → API — HTTP simple actuellement.
- [ ] **Réseau privé étanche pour `database_api`** — le port est publié
  directement sur l'hôte (`8001:8000` dans
  [docker-compose.yml:65](docker-compose.yml:65)) alors que le cahier des
  charges exige qu'il soit strictement inaccessible depuis l'extérieur du
  cluster.

## 🟠 Tests — couverture ≥ 80% (API IA, API Database, UI)

- [x] `database` : 100% (htmlcov).
- [ ] `api` (API IA) : aucun rapport de couverture généré, à vérifier.
- [ ] `frontend` (UI) : `pytest`/`pytest-cov` **absents** de
  [frontend/pyproject.toml](frontend/pyproject.toml) malgré l'existence de
  tests ([frontend/tests/](frontend/tests/), [frontend/test_app.py](frontend/test_app.py))
  — à déclarer avant de pouvoir mesurer la couverture.
- [ ] CI ([.github/workflows/docker.yml](.github/workflows/docker.yml)) ne
  lance les tests que pour `agents` avant le build/push Docker — `api`,
  `database`, `frontend` ne sont jamais testés en CI.
- [ ] Aucun seuil de couverture appliqué en CI.

## 🟡 Documentation

- [ ] Aucune trace de Sphinx (`conf.py`, `.rst`). À mettre en place : doc
  auto des deux API, schéma relationnel de la base
  ([database/tables/](database/tables/)), cartographie du graphe multi-agent
  ([agents/graph.py](agents/graph.py)).

## 🟡 Monitoring

- [ ] [monitoring/docker-compose.yml](monitoring/docker-compose.yml)
  (Langfuse full stack + Uptime Kuma) est **séparé** de la stack principale
  ([docker-compose.yml](docker-compose.yml)) — pas de "stack Docker unifiée"
  au sens du cahier des charges.
- [ ] Uptime Kuma présent mais pas de confirmation que les 3 composants
  (API IA, API Database, Frontend) sont effectivement sondés.

## 🟡 Gouvernance

- [ ] Aucun template d'issue GitHub (`.github/ISSUE_TEMPLATE/`) — le cahier
  des charges demande que chaque anomalie soit archivée en GitHub Issues.

## Dette déjà connue (hors scope Partie 3, cf. CLAUDE.md)

- [ ] `SUPABASE_PASSWORD` avec valeur par défaut placeholder dans
  [database/connection.py](database/connection.py) au lieu d'un refus de
  démarrage explicite (fail-closed).
