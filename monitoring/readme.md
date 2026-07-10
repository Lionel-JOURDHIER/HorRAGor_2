# langfuse

Email:
admin@horragor.local

Password:
Admin123456!

# HorRAGor — Monitoring multi-agent avec Langfuse

## Description

HorRAGor est une application multi-agent basée sur **LangGraph** permettant de rechercher et recommander des films à partir d'un index FAISS enrichi.

Cette version intègre **Langfuse** pour le monitoring des agents IA.

Langfuse permet de :

* tracer chaque exécution d'un agent ;
* visualiser les étapes d'un graphe LangGraph ;
* mesurer la latence des appels LLM ;
* suivre la consommation de tokens ;
* analyser les erreurs ;
* préparer des métriques pour le frontend.

Architecture utilisée :

```
                    Frontend Streamlit
                           |
                           |
                      FastAPI API
                           |
                           |
                     LangGraph Agent
                           |
          ---------------------------------
          |               |               |
       Router          Search          Validator
          |
       ChatOllama
          |
       Langfuse Callback
          |
       Langfuse Server
          |
  ---------------------------------
  PostgreSQL  ClickHouse  Redis  MinIO
```

# 1. Prérequis

Installer :

* Docker Desktop
* Python 3.11+
* Git

Vérifier Docker :

```bash
docker --version
docker compose version
```

# 2. Structure du projet

Exemple :

```
HorRAGor_2/

├── api/
│   ├── main.py
│   ├── routes.py
│   ├── routes_monitoring.py
│   │
│   └── monitoring/
│       ├── langfuse_client.py
│       ├── langfuse_callback.py
│       └── monitoring_service.py
│
├── frontend/
│   └── streamlit_app.py
│
├── monitoring/
│   └── langfuse/
│       ├── docker-compose.yml
│       └── .env
│
└── docker-compose.yml
```

# 3. Installation de Langfuse

Le serveur Langfuse est lancé avec Docker Compose.

Aller dans :

```bash
cd monitoring/langfuse
```

Lancer les services :

```bash
docker compose up -d
```

Vérifier :

```bash
docker ps
```

Services démarrés :

| Service         | Fonction                  |
| --------------- | ------------------------- |
| langfuse-web    | Interface Web Langfuse    |
| langfuse-worker | Traitement des événements |
| postgres        | Base Langfuse             |
| clickhouse      | Stockage analytique       |
| redis           | Queue                     |
| minio           | Stockage objet S3         |

Accès interface :

```
http://localhost:3000
```

# 4. Configuration Langfuse

Créer les variables dans `.env` :

```env
LANGFUSE_HOST=http://langfuse-web:3000

LANGFUSE_PUBLIC_KEY=xxxxxxxx
LANGFUSE_SECRET_KEY=xxxxxxxx
```

Ces clés sont disponibles dans :

```
Langfuse UI
→ Project Settings
→ API Keys
```

# 5. Connexion FastAPI - Langfuse

Le client Langfuse est centralisé dans :

```
api/monitoring/langfuse_client.py
```

Exemple :

```python
from langfuse import Langfuse
import os


langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    base_url=os.getenv("LANGFUSE_HOST")
)
```

# 6. Callback LangGraph

Le callback permet de tracer automatiquement les appels LangChain/LangGraph.

Fichier :

```
api/monitoring/langfuse_callback.py
```

Utilisation :

```python
config = {
    "callbacks": [
        langfuse_handler
    ]
}


graph.invoke(
    state,
    config=config
)
```

Les traces visibles dans Langfuse :

* POST /chat/response
* LangGraph execution
* title_router
* filter_and_search_hybrid
* ChatOllama
* validator

# 7. Service de métriques

Le service :

```
api/monitoring/monitoring_service.py
```

Responsabilités :

* récupération des traces Langfuse ;
* calcul des statistiques ;
* préparation des données frontend.

Exemple de métriques :

```json
{
  "total_traces": 12,
  "average_latency_ms": 37000,
  "input_tokens": 1200,
  "output_tokens": 500,
  "total_tokens": 1700
}
```

# 8. Endpoint Monitoring API

Le router :

```
api/routes_monitoring.py
```

Expose les métriques :

## GET /monitoring/metrics

Exemple :

```bash
curl http://localhost:8000/monitoring/metrics
```

Réponse :

```json
{
  "total_traces": 12,
  "average_latency_ms": 32000,
  "input_tokens": 950,
  "output_tokens": 240,
  "total_tokens": 1190
}
```

## GET /monitoring/traces

Retourne les dernières traces Langfuse.

# 9. Lancement complet HorRAGor

## Démarrer Langfuse

```bash
cd monitoring/langfuse

docker compose up -d
```

## Démarrer API

Depuis la racine :

```bash
docker compose up horragor_api
```

Vérification :

```
http://localhost:8000/docs
```

## Démarrer Frontend

```bash
streamlit run frontend/streamlit_app.py
```

# 10. Vérification du réseau Docker

Les containers doivent être dans le même réseau :

```
horragor_2_horragor_net
```

Vérifier :

```bash
docker network inspect horragor_2_horragor_net
```

Services attendus :

```
horragor_api
horragor_frontend
langfuse-web
langfuse-worker
postgres
clickhouse
redis
minio
```

# 11. Dépannage

## Langfuse ne reçoit aucune trace

Vérifier :

```bash
docker logs horragor_api
```

Tester la connexion :

```bash
curl http://langfuse-web:3000
```

Tester depuis API :

```bash
docker exec -it horragor_api bash

getent hosts langfuse-web
```

## Erreur PostgreSQL P1000

Cause :

* mauvais utilisateur/password ;
* ancien volume Docker.

Solution :

Arrêter les services :

```bash
docker compose down
```

Supprimer les volumes Langfuse :

```bash
docker volume rm langfuse_langfuse_postgres_data
```

Puis redémarrer :

```bash
docker compose up -d
```

## Erreur Unauthorized 401

Vérifier :

```
LANGFUSE_PUBLIC_KEY
LANGFUSE_SECRET_KEY
```

Les clés doivent correspondre au projet Langfuse utilisé.

# 12. Résultat attendu

Dans Langfuse UI :

```
Traces

POST /chat/response

    LangGraph

        title_router

        filter_and_search_hybrid

        ChatOllama

        validator
```

Chaque exécution affiche :

* durée totale ;
* étapes du graphe ;
* modèles utilisés ;
* tokens consommés ;
* erreurs éventuelles.

# Conclusion

L'intégration Langfuse transforme HorRAGor en système multi-agent observable.

Elle permet :

* le suivi des performances LLM ;
* l'analyse des coûts ;
* le debug des agents ;
* l'exposition des métriques au frontend Streamlit ;
* l'amélioration continue du système IA.
