"""agents/prompts.py
Module de centralisation des gabarits de requêtes (Prompt Templates) de l'agent.

Ce fichier regroupe l'ensemble des instructions système (System Prompts) et des
gabarits de messages utilisés pour configurer le comportement des LLM au sein
des différents nœuds du graphe. Isoler les prompts ici permet d'itérer rapidement
sur le comportement du modèle sans modifier le code logique du workflow (respect
du principe KISS).

Prompts centralisés à définir :
    - System Prompt de Classification : Oriente le LLM pour détecter l'intention de
      l'utilisateur (recherche directe, sémantique ou bavardage).
    - System Prompt d'Extraction : Guide le LLM pour isoler les entités nommées et
      critères de filtrage (réalisateur, genre, année) à partir du texte brut.
    - System Prompt de Synthèse (RAG) : Structure la réponse finale de l'agent en lui
      imposant d'intégrer le Top 5 des films recommandés avec leurs métadonnées exactes.

Dépendances principales :
    - langchain_core.prompts (ChatPromptTemplate, MessagesPlaceholder)

Auteur/Responsable : Équipe Agents
"""
