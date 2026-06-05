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

## 🔑 Configuration & Sécurité

La connexion s'appuie sur des variables d'environnement chargées via un fichier `.env`. 

### Pooler Supabase & Résilience
Pour absorber les requêtes en parallèle (API FastAPI + scripts d'indexation) et éviter la saturation du réseau, le moteur configure un pool de connexions optimisé :
* **`pool_size=5`** & **`max_overflow=10`** : Allocation dynamique des connexions.
* **`pool_pre_ping=True`** : Test systématique de la viabilité de la connexion avant exécution (indispensable pour prévenir les déconnexions intempestives du pooler Supabase).

---

## 🔍 Logique Métier & Requêtes (`queries.py`)

Le fichier `queries.py` sert de pont unique entre tes modèles de tables SQLAlchemy et tes schémas d'API Pydantic. Il intègre les fonctionnalités clés suivantes :

1. **Jointure Multi-Tables (Format Détaillé) :** Centralise l'extraction de l'entité `Film` en y greffant l'ensemble de ses métadonnées critiques distantes (`ScoresTmdb`, `ScoresImdb`, `ScoresRt`), son `Realisateur` et sa `Collection` via des jointures externes (`outerjoin`).
2. **Résolution Many-to-Many :** Extrait efficacement la liste des genres associés à un film en passant par la table pivot `FilmGenre`.
3. **Calcul de Score Agrégé :** Calcule dynamiquement une note critique globale harmonisée sur une base 100 en ignorant strictement les valeurs `None` (Null en base de données) afin de ne pas fausser les statistiques.
4. **Extraction en Lot (Format Court) :** Permet à partir d'une liste d'identifiants (par exemple retournée par **FAISS**) d'extraire en une seule passe (`.in_()`) les métadonnées compactes des films, évitant ainsi le piège de performance des requêtes répétitives (problème du N+1 query).

---

## 🙋‍♂️ F.A.Q. du Développeur API : Guide des Endpoints et Appels

Voici la cartographie exacte des routes de ton API FastAPI et leur correspondance directe avec les fonctions du module `queries.py` :

### 1. Page de Détails d'un Film (Fiche Complète)
* **Route API :** `GET /api/v1/films/{tmdb_id}`
* **Fonction à appeler :** `get_film_details_by_id(session, tmdb_id)`
* **Type renvoyé par la requête :** `Optional[FilmDetail]`
* **Description :** Cet appel est conçu pour la vue principale d'un film. Il effectue une jointure Merise complète (5 jointures externes) pour récupérer les métadonnées globales, résout la relation Many-to-Many pour les genres et calcule en direct le score agrégé nettoyé des valeurs `None`.

### 2. Résultats de Recherche Vectorielle / Recommandations
* **Route API :** `POST /api/v1/recommendations` ou `GET /api/v1/search`
* **Fonction à appeler :** `get_films_short_by_ids(session, tmdb_ids)`
* **Type renvoyé par la requête :** `List[FilmShort]`
* **Description :** Cet appel intervient immédiatement après que ton service **FAISS** a retourné les identifiants de films les plus proches. Pour éviter de saturer Supabase (problème du N+1), la fonction exécute **seulement 2 requêtes SQL hautement optimisées** (une pour les films/scores via un opérateur `.in_()`, une pour grouper tous les genres associés). Elle réordonne ensuite le résultat en mémoire pour respecter le classement de pertinence FAISS.

### 3. Filtre de Recherche par Réalisateur
* **Route API :** `GET /api/v1/directors`
* **Fonction à appeler :** `get_all_directors(session)`
* **Type renvoyé par la requête :** `DirectorsResponse`
* **Description :** Renvoie la liste globale de tous les réalisateurs présents dans la base Supabase. La requête SQL utilise un `.distinct()` et un `.order_by()` pour fournir une liste propre et triée alphabétiquement, idéale pour alimenter un composant de sélection (Dropdown) dans ton interface utilisateur.

### 4. Filtre de Recherche par Genre
* **Route API :** `GET /api/v1/genres`
* **Fonction à appeler :** `get_all_genres(session)`
* **Type renvoyé par la requête :** `GenresResponse`
* **Description :** Renvoie la liste unique de tous les genres disponibles en base de données. Tout comme pour les réalisateurs, les doublons sont éliminés à la source via SQL pour alléger le transit réseau et le parsing Pydantic.

---

## ⚠️ Rappel Crucial : Gestion des Sessions et Cycle de Vie

Pour **toutes** ces routes d'API, l'injection de la session dans tes endpoints FastAPI doit impérativement utiliser le système d'injection de dépendances : **`Depends(get_db)`**.

```python
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database.connection import get_db
from database import queries

app = FastAPI()

@app.get("/api/v1/films/{tmdb_id}", response_model=queries.FilmDetail)
def get_movie_catalog_detail(tmdb_id: int, db: Session = Depends(get_db)):
    # L'appel à la base de données via notre requête SQLAlchemy Pure
    movie_details = queries.get_film_details_by_id(db, tmdb_id)
    
    if not movie_details:
        raise HTTPException(status_code=404, detail="Film introuvable dans le catalogue.")
        
    return movie_details
```

