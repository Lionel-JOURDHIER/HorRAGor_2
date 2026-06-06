# ⚡ HorRAGor — Guide de Démarrage Rapide (Quickstart)

Ce guide permet de lancer et de gérer l'intégralité de la stack locale **HorRAGor** (Ollama GPU + API FastAPI + Frontend Streamlit) à l'aide de Docker Compose.

---

## 🛠️ Prérequis Système

Avant de commencer, assurez-vous d'avoir installé sur votre machine hôte :
1. **Docker** et **Docker Compose** v2+.
2. **NVIDIA Container Toolkit** (indispensable pour que le conteneur Ollama puisse exploiter la puissance de la carte graphique locale, ex: RTX 4060).
3. Les modèles Ollama déjà téléchargés en local (évite de devoir re-télécharger des Go de données dans le conteneur).
--- 
## 🚀 Étape 1 : Configuration de l'Environnement (`.env`)

Créez un fichier `.env` à la racine du projet (au même niveau que le fichier `docker-compose.yml`) et collez-y les configurations suivantes en complétant vos identifiants Supabase et verifier le path pour le dossier .ollama:

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

# ─── OLLAMA ───────────────────────────────────────────────────────────────────
# En local : http://localhost:11434
# En Docker : http://ollama:11434 (injecté automatiquement par docker-compose)
OLLAMA_BASE_URL=http://ollama:11434

# ─── FAISS (chemins internes au conteneur) ────────────────────────────────────
FAISS_INDEX_PATH=/app/faiss_data/horragor.index
FAISS_MAPPING_PATH=/app/faiss_data/horragor_mapping.json

# ─── STOCKAGE DES MODÈLES OLLAMA (HÔTE) ───────────────────────────────────────
# Décommentez la ligne qui correspond à votre système d'exploitation :

# Pour les utilisateurs LINUX :
OLLAMA_MODELS_PATH=/home/[votre utilisateur LINUX]/.ollama

# Pour les utilisateurs WINDOWS (PC) :
# OLLAMA_MODELS_PATH=C:\Users\[votre nom utilisateur WINDOWS]\.ollama
```
> ⚠️ **NOTE IMPORTANTE :** Assurez-vous d'avoir déjà téléchargé les modèles Ollama sur votre système hôte avant de lancer la stack Docker (ex: `granite4.1:8b`, `qwen3-embedding:0.6b`).

---

## 📦 Étape 2 : Lancement et Gestion de la Stack
### 🟦 Premier démarrage (Build & Initialisation)
Cette commande construit les images Docker et déclenche la première synchronisation de l'index FAISS depuis Supabase.
```bash
docker compose up --build
```

### 🟩 Démarrages suivants (Chargement rapide)
Une fois l'index FAISS initialisé et persisté dans le volume, les démarrages suivants se font à chaud en environ 2 secondes.
```bash
docker compose up -d
```

### 🟧 Forcer un rebuild complet de l'index FAISS
Si les données sur Supabase ont changé et que vous devez reconstruire l'index vectoriel local à partir de zéro, videz le volume persistant avant de relancer :
```bash
docker volume rm horragor_faiss_data && docker compose up -d
```
--- 
## 🌐 Étape 3 : Accès aux Applications

Une fois la stack démarrée avec succès, les interfaces suivantes sont disponibles :
| Composant | URL Locale | Description |
| :--- | :--- | :--- |
| 🎬 **Frontend** | [http://localhost:8501](http://localhost:8501) | Interface Streamlit pour dialoguer avec l'agent et ajuster les filtres. |
| ⚙️ **API REST** | [http://localhost:8000/docs](http://localhost:8000/docs) | Documentation Swagger interactive de FastAPI (conçue par Hanna). |
| 🧠 **Ollama** | [http://localhost:11434](http://localhost:11434) | Endpoint du moteur d'inférence LLM local. |

## 🛠️ Diagnostics et Maintenance
### Suivre les logs d'un service spécifique
Idéal pour analyser le comportement de l'agent LangGraph ou le chargement de l'API de Hanna sans être pollué par les logs d'Ollama :
```bash
docker compose logs -f api
```

### Arrêter proprement la stack
```bash
docker compose down
```