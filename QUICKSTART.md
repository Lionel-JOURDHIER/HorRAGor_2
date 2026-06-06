# ⚡ HorRAGor — Guide de Démarrage Rapide (Quickstart)

Ce guide permet de lancer et de gérer l'intégralité de la stack locale **HorRAGor** (Ollama GPU + API FastAPI + Frontend Streamlit) à l'aide de Docker Compose.

---

## 🛠️ Prérequis Système

Avant de commencer, assurez-vous d'avoir installé sur votre machine hôte :
1. **Docker** et **Docker Compose** v2+.
2. **NVIDIA Container Toolkit** (indispensable pour que le conteneur Ollama puisse exploiter la puissance de la carte graphique locale, ex: RTX 4060).
3. Les modèles Ollama déjà téléchargés en local (évite de devoir re-télécharger des Go de données dans le conteneur).

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