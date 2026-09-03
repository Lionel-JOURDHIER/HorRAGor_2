# Présentation du projet

HorRAGor est une application de recherche et de recommandation de films
d'horreur basée sur une architecture **RAG (Retrieval-Augmented Generation)**
et un système **multi-agent développé avec LangGraph**.

## Objectif

L'objectif de HorRAGor est de permettre à l'utilisateur d'interroger une
base de données cinématographique en langage naturel et d'obtenir des
réponses pertinentes à partir de plusieurs sources de données.

L'application permet notamment de rechercher des films selon différents
critères et de poser des questions nécessitant une combinaison de recherche
dans les données, de recherche vectorielle et de génération de texte.

## Architecture

HorRAGor est organisé en plusieurs composants indépendants :

* **Frontend** : interface utilisateur développée avec Streamlit.
* **API d'intelligence** : API FastAPI responsable de l'orchestration du
  graphe multi-agent LangGraph.
* **API Database** : API dédiée à l'accès aux données et à l'index vectoriel.
* **Base de données** : stockage relationnel PostgreSQL contenant les
  informations sur les films.
* **Index vectoriel** : index FAISS utilisé pour la recherche sémantique.
* **Monitoring** : Prometheus, Grafana, Uptime Kuma et Langfuse permettent
  de surveiller les différents composants et le graphe multi-agent.

## Architecture générale

Le fonctionnement global de l'application peut être résumé ainsi :

.. code-block:: text

Utilisateur
|
v
Streamlit
|
v
API FastAPI
|
v
Graphe LangGraph
|
+-------------------+
|                   |
v                   v
API Database       Recherche Wikipedia
|
+-----------+
|           |
v           v
PostgreSQL     FAISS

## Technologies

Le projet utilise principalement les technologies suivantes :

* **Python**
* **FastAPI**
* **Streamlit**
* **LangGraph**
* **LangChain**
* **Ollama**
* **FAISS**
* **PostgreSQL**
* **SQLAlchemy**
* **Docker**
* **Prometheus**
* **Grafana**
* **Uptime Kuma**
* **Langfuse**

## Fonctionnement

Lorsqu'un utilisateur envoie une question depuis l'interface Streamlit,
la requête est transmise à l'API d'intelligence.

L'API transmet ensuite la requête au graphe LangGraph. Le routeur détermine
les agents et les outils nécessaires pour traiter la demande.

Selon la question, le système peut utiliser :

* les données relationnelles de la base PostgreSQL ;
* la recherche vectorielle avec FAISS ;
* les informations provenant de Wikipedia ;
* le modèle de langage exécuté localement avec Ollama.

Les résultats récupérés sont ensuite utilisés par le système multi-agent
pour construire une réponse en langage naturel.

## Séparation des services

L'architecture sépare l'accès aux données de la logique d'intelligence.

L'**API Database** est responsable de l'accès à la base PostgreSQL et expose
des endpoints dédiés aux autres composants.

L'**API d'intelligence** ne communique donc pas directement avec PostgreSQL :
elle utilise l'API Database pour accéder aux données.

Cette séparation permet d'améliorer la sécurité, la modularité et la
maintenabilité de l'application.

## Monitoring

Le projet dispose d'une infrastructure de monitoring permettant de suivre
l'état et les performances des différents composants de l'application.

**Prometheus** collecte les métriques exposées par les trois composants
principaux :

* l'API d'intelligence ;
* l'API Database ;
* le frontend.

**Grafana** permet de visualiser ces métriques à travers des tableaux de
bord dédiés et de suivre notamment l'activité, les performances et l'état
des services.

**Uptime Kuma** est utilisé pour surveiller la disponibilité des différents
services et détecter les interruptions.

Pour le système multi-agent, **Langfuse** fournit un monitoring spécifique
des interactions avec le graphe LangGraph. Il permet notamment de suivre
les traces, les appels aux modèles et le fonctionnement des agents.

Cette architecture permet ainsi de distinguer le monitoring technique des
services (Prometheus, Grafana, Uptime Kuma) du monitoring spécifique du
système d'intelligence artificielle (Langfuse).


## Déploiement

L'ensemble des composants est conteneurisé avec **Docker** et peut être
exécuté dans un environnement local basé sur **WSL2**.

Les services sont organisés avec Docker Compose afin de faciliter le
déploiement et la communication entre les différents conteneurs.

## CI/CD et qualité

Le projet utilise **GitHub Actions** pour automatiser le pipeline
CI/CD.

Le pipeline comprend notamment :

* l'installation des dépendances ;
* l'exécution des tests ;
* les contrôles de qualité du code ;
* la génération de la documentation Sphinx ;
* la construction des images Docker ;
* la publication des images sur GitHub Container Registry ;
* la publication de la documentation sur GitHub Pages.

## Documentation technique

La documentation présente ensuite les différents composants du projet :

* **API** : endpoints et services de l'API d'intelligence ;
* **Agents et LangGraph** : architecture du système multi-agent ;
* **Couche données** : API Database, requêtes et modèles ;
* **Schéma de la base de données** : tables et relations ;
* **Cartographie LangGraph** : représentation graphique du graphe multi-agent.

