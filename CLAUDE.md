# HorRAGor

@.claude/standards/socle-code.md

<!-- Ne dupliquez rien du socle ici. Ce fichier ne contient que ce qui est vrai
     pour CE dépôt et que Claude ne peut pas déduire du code. Cible : 60 lignes.
     Les commentaires HTML de ce type sont retirés avant injection dans le
     contexte : ils ne coûtent rien et servent de notes au mainteneur. -->

Assistant conversationnel RAG sur un corpus films (TMDB/IMDB) : API FastAPI +
agent LangGraph (routage RAG / Wikipedia / narrateur) + frontend Streamlit,
index vectoriel FAISS reconstruit depuis une base Supabase distante, LLM local
via Ollama.

## Commandes

| | |
|---|---|
| Lancer (stack complète) | `docker compose up --build` (premier démarrage), `docker compose up -d` ensuite |
| Lint / format | `uv run ruff check` / `uv run ruff format` (dans `api/`, `agents/`, `database/`, `frontend/` — chacun a son propre `pyproject.toml`/`uv.lock`) |
| Tests | `uv run pytest` (dans chacun des quatre sous-projets) |
| Activer les hooks (une fois par machine) | `git config core.hooksPath .githooks` |

## Ce qui est spécifique à ce projet

- **Quatre sous-projets indépendants**, chacun avec son `pyproject.toml`/`uv.lock` :
  `api/` (FastAPI + LangChain/LangGraph), `agents/` (graphe LangGraph : routeur,
  nœuds RAG/Wikipedia/narrateur), `database/` (SQLAlchemy + client Supabase,
  service FAISS), `frontend/` (Streamlit). Pas de `pyproject.toml` à la racine —
  ne pas en créer un qui les fusionnerait.
- **Docstrings** : triple guillemets, en-tête `"""chemin/fichier.py` suivi d'un
  paragraphe de contexte (voir `logger.py`, `database/connection.py`) — proche
  du Google-style sans sections `Args:`/`Returns:` systématiques sur tous les
  modules existants ; les ajouter sur toute fonction nouvelle ou modifiée.
- **Journalisation** : loguru déjà en place via `logger.py` (`setup_logger()` /
  `get_logger(module)`), jamais de `print()` ni de `logging` standard. Trois
  sorties déjà configurées : console (DEBUG), `logs/app.log` (INFO, rotation
  10 MB/7 j), `logs/error.log` (ERROR, rotation 5 MB/14 j) — ne pas dupliquer
  cette configuration ailleurs, importer `get_logger` depuis la racine.
- **Secrets** : `.env` (jamais commité, `.env.example` tenu à jour) — identifiants
  Supabase (`SUPABASE_*`), Postgres local, chemins Ollama/FAISS. `database/connection.py`
  a un `DB_PASSWORD` avec valeur par défaut placeholder (`"<MOT_DE_PASSE>"`) au
  lieu d'un fail-closed strict — à corriger si retouché, pas dans le cadre de
  cette installation.
- **Tests** : par sous-projet, dans son propre dossier `tests/`. Pas de test
  d'intégration Docker Compose pour l'instant.
- **Commit** : format standard `type : description`, pas d'extension observée.

## Dette existante

- `database/connection.py` — valeur par défaut placeholder sur `SUPABASE_PASSWORD`
  au lieu d'un refus de démarrage explicite (`rules/python.md` § Secrets /
  fail-closed) : à corriger dans une branche dédiée, pas au détour d'un correctif.

## Pièges déjà payés

- Ollama tourne sur l'hôte, pas dans `docker-compose.yml` (bloc commenté) :
  `OLLAMA_BASE_URL` doit pointer vers `http://host.docker.internal:11434` côté
  conteneur API, pas `http://ollama:11434`.
- Le volume `horragor_faiss_data` persiste l'index entre redémarrages ; après
  une modification des données Supabase, il faut `docker volume rm
  horragor_faiss_data` avant de relancer, sinon l'index reste périmé.

## Après validation

```bash
git checkout dev
git pull
docker compose up -d
```

Fusionner `dev` dans `main` une fois la validation confirmée — sur demande
explicite uniquement.

---

<!-- Règles par langage : ne PAS les mettre ici, et ne pas les écrire à la main.
     Le sous-module en contient dix-sept, déjà rédigées et versionnées, dans
     .claude/standards/rules/ : python, tests-python, javascript, nodejs, vba,
     ml, donnees, bdd, deploiement, securite-api, agents-ia, streamlit,
     selenium, cicd, http, documentation, workflow-session.

     On copie celles qui servent, une par une, comme décrit dans le README du
     sous-module :

       cp .claude/standards/rules/python.md .claude/rules/python.md

     Chacune porte un frontmatter `paths` et ne se charge que sur les fichiers
     correspondants : un projet VBA ne charge jamais les règles ruff, et
     inversement. Ne recopier que les règles des langages et des composants
     présents — une règle chargée pour rien coûte du contexte à chaque session.

     Ce qui ne vaut que pour CE dépôt va dans le présent fichier, pas dans
     .claude/rules/, dont le contenu est celui du dépôt de standards et se fait
     écraser à chaque mise à jour. -->
