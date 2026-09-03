# ⚡ HorRAGor — Guide de Démarrage Rapide (Quickstart)

Ce guide permet de lancer et de gérer l'intégralité de la stack locale **HorRAGor** (API Database + API IA FastAPI + Frontend Streamlit) à l'aide de Docker Compose. **Ollama tourne sur la machine hôte**, pas dans un conteneur.

---

## 🛠️ Prérequis Système

Avant de commencer, assurez-vous d'avoir installé sur votre machine hôte :
1. **Docker** et **Docker Compose** v2+.
2. **Ollama** installé et démarré localement (`http://localhost:11434`).
3. Les modèles Ollama déjà téléchargés en local (voir Étape 2).
4. Un accès à un projet **Supabase** (identifiants du pooler).

---
## 🚀 Étape 1 : Configuration de l'Environnement (`.env`)

Créez un fichier `.env` à la racine du projet (au même niveau que `docker-compose.yml`) à partir de `.env.example`, et complétez vos identifiants Supabase :

```toml
# ─── CONFIGURATION POSTGRES LOCAL ─────────────────────────────────────────────
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=horror_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# ─── CONFIGURATION SUPABASE DISTANT ───────────────────────────────────────────
SUPABASE_PROJECT=[PROJET SUPABASE]
SUPABASE_PUBLISHABLE_KEY=[SUPABASE PUBLISHABLE KEY]
SUPABASE_PASSWORD=[MOT DE PASSE]
SUPABASE_DB=postgres
SUPABASE_PORT=6543
SUPABASE_USER=postgres.[PROJET SUPABASE]
SUPABASE_HOST=aws-1-eu-west-3.pooler.supabase.com

# ─── OLLAMA (hôte) ─────────────────────────────────────────────────────────
# Cette valeur est utilisée si vous lancez l'API hors Docker.
# Dans docker-compose.yml, le conteneur `api` écrase cette variable avec
# http://host.docker.internal:11434 pour atteindre l'Ollama de l'hôte.
OLLAMA_BASE_URL=http://localhost:11434

# ─── FAISS (chemins internes au conteneur) ────────────────────────────────────
# Rappel : docker-compose.yml écrase ces deux valeurs pour le conteneur `api`
# (chemins relatifs à /app). Elles ne servent qu'à un lancement hors Docker.
FAISS_INDEX_PATH=/app/faiss_data/horragor.index
FAISS_MAPPING_PATH=/app/faiss_data/horragor_mapping.json
```

> ⚠️ **NOTE IMPORTANTE :** téléchargez les modèles Ollama sur votre système hôte avant de lancer la stack (voir Étape 2). Le conteneur `api` ne peut pas les télécharger lui-même : il appelle l'Ollama de l'hôte via `host.docker.internal`.

---

## 📦 Étape 2 : Modèles Ollama (sur l'hôte)

Ollama s'exécute directement sur la machine hôte, pas dans Docker. Téléchargez les modèles nécessaires en local avant de démarrer la stack :

```bash
# Modèle de langage
ollama pull granite4.1:3b

# Modèle d'embedding
ollama pull qwen3-embedding:0.6b
```

Ces modèles sont stockés dans `~/.ollama` (ou le chemin configuré) et restent disponibles pour tous vos projets.

---

## 🐳 Étape 3 : Lancement et Gestion de la Stack

### 🟦 Premier démarrage (Build & Initialisation)

```bash
docker compose up --build
```

Cette commande construit les images `database_api`, `api` et `frontend`. L'index FAISS présent dans `faiss_data/` à la racine du dépôt est **copié dans l'image `api`** au moment du build : le conteneur le charge depuis `/app/faiss_data/`, sans volume ni synchronisation au démarrage.

> ⚠️ L'index n'est pas reconstruit automatiquement. `faiss_data/horragor.index` doit exister avant le build, sinon l'API refuse de démarrer.

### 🟩 Démarrages suivants (Chargement rapide)

L'index étant dans l'image, les démarrages suivants ne refont aucun travail d'indexation :

```bash
docker compose up -d
```

### 🟧 Rafraîchir l'index FAISS

Si les données sur Supabase ont changé, régénérez `faiss_data/` puis reconstruisez l'image `api` — c'est le build qui embarque l'index, un simple `up -d` réutiliserait l'ancien :

```bash
docker compose build api && docker compose up -d
```

---

## 🌐 Étape 4 : Accès aux Applications

| Composant | URL Locale | Description |
| :--- | :--- | :--- |
| 🎬 **Frontend** | [http://localhost:8501](http://localhost:8501) | Interface Streamlit pour dialoguer avec l'agent et ajuster les filtres. |
| ⚙️ **API IA** | [http://localhost:8000/docs](http://localhost:8000/docs) | Documentation Swagger de l'API IA (agent LangGraph, chat, Wikipedia, monitoring). |
| 🗄️ **API Database** | [http://localhost:8001/docs](http://localhost:8001/docs) | Documentation Swagger de l'API dédiée aux données (films, genres, réalisateurs). |
| 🧠 **Ollama** | [http://localhost:11434](http://localhost:11434) | Endpoint du moteur d'inférence LLM, exécuté sur l'hôte. |

---

## 🛠️ Diagnostics et Maintenance

### Suivre les logs d'un service spécifique

```bash
docker compose logs -f api
docker compose logs -f database_api
docker compose logs -f frontend
```

### Arrêter proprement la stack

```bash
docker compose down
```
