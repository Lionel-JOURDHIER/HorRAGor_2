# 🎬 HorRAGor

HorRAGor est une application de recommandation et d'analyse de films d'horreur. Alliant la puissance d'un moteur d'agent conversationnel intelligent (**LangGraph**, **Ollama** local) et la rigueur de filtres relationnels, elle permet aux utilisateurs d'explorer une base de données dédiée et d'obtenir des suggestions ultra-ciblées.

L'architecture est entièrement conteneurisée et pensée pour s'exécuter localement sous **WSL2 (Ubuntu)** afin de garantir un traitement souverain et sécurisé des données.

---

## 🛠️ Stack Technique

* **Front-End** : Streamlit (Python)
* **Back-End API** : FastAPI & Pydantic
* **Orchestration IA** : LangGraph & LangChain (Modèles locaux via Ollama)
* **Base de Données** : Supabase (PostgreSQL) exploité via **SQLAlchemy**
* **Recherche Sémantique** : Index vectoriel **FAISS** chargé en RAM
* **Environnement** : Docker Compose, WSL2 (Ubuntu)

---

## 📂 Architecture du Projet

Le projet est découpé en composants autonomes (KISS/DRY), chacun disposant de son propre environnement et de ses dépendances :

```text
HORRAGOR_2/
├── agents/             # Moteur de l'agent intelligent
│   ├── tools/          # Outils de l'agent (SQL, FAISS, Wikipédia)
│   ├── graph.py        # Assemblage et orchestration du StateGraph
│   ├── nodes.py        # Logique métier associée à chaque étape du graphe
│   ├── state.py        # Structure de données circulante (AgentState)
│   └── prompts.py      # Centralisation de l'ingénierie des invites (System Prompts)
├── api/                # Couche de services REST (FastAPI)
│   ├── modules/
│   │   └── routes.py   # Exposition des endpoints (/chat, /id_film, /list_réal...)
│   ├── main.py         # Point d'entrée du serveur de l'API
│   └── schemas.py      # Contrats d'échange et modèles de validation Pydantic
├── app/                # Interface utilisateur (Streamlit)
│   ├── pages/          # Vues et onglets secondaires de l'application
│   └── app.py          # Point d'entrée IHM avec le formulaire de préférences
├── database/           # Persistance et recherche vectorielle
│   ├── connection.py   # Initialisation de la session de base de données
│   ├── faiss_service.py# Gestion globale de l'index vectoriel en RAM
│   ├── models.py       # Définition des tables et entités avec SQLModel
│   └── populate.py     # Script d'initialisation et d'ingestion des données
├── docker-compose.yml  # Orchestration multi-conteneurs locale
├── .gitignore          # Protections des index, variables d'environnement et caches
└── .env.example        # Modèle de configuration des variables d'environnement
```
---
## 🚦 Endpoints de l'API
L'API managée par Hanna expose les points d'accès suivants :

- GET /health : État de santé de l'API et du cache FAISS.
- GET /id_film : Récupération des informations complètes d'un film par son ID Supabase.
- GET /list_real : Liste exhaustive des réalisateurs présents en base.
- GET /list_genre : Liste exhaustive des genres cinématographiques.
- POST /chat : Requête de discussion asynchrone (retourne l'état de réflexion de l'agent, la réponse du LLM et le Top 5 des films recommandés).
- GET /wikipedia : Extraction dynamique du synopsis depuis Wikipédia si nécessaire.

---
## 🎛️ Formulaire de Préférences (IHM)
L'interface conçue pour les utilisateurs permet d'ajuster les préférences en temps réel grâce à un formulaire physique strict :

- Filtres textuels/catégoriels : Sélection du réalisateur, genres à conserver, genres non souhaités.
- Filtres numériques (Sliders) :
  - Année de sortie : de 1900 à 2026.
  - Score TMDB : de 0 à 10.
  - Durée du film : de 1 à 685 minutes.

