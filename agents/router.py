"""agents/router.py
Module de routage conditionnel et d'aiguillage du graphe HorRAGor v3.

Ce fichier centralise exclusivement la logique de transition et les embranchements
dynamiques (Conditional Edges) de la Machine à États Finis (FSM) de l'agent. Il ne
contient aucune implémentation de nœud (exécutée dans nodes.py), garantissant ainsi
une séparation stricte entre la logique de décision de trajectoire et l'exécution.

En se basant sur les variables d'état de l'AgentState, ce module implémente les fonctions
d'aiguillage suivantes à travers les 3 phases du programme :

================================================================================
PHASE 1 : AIGUILLAGE DE L'INTENTION ET DE L'ENTRÉE (LE CERVEau)
================================================================================
Aiguille le flux dès la réception du message utilisateur pour séparer les requêtes
de recherche lourdes des interactions conversationnelles (Bypass).

    - route_by_intent : Analyse l'intention déterminée dans le state pour orienter :
        * Vers le pipeline de RECHERCHE (Processus RAG dans nodes.py).
        * Vers le bypass de DISCUSSION (Chargement du contexte mémorisé).
        * Vers le pipeline de RECHERCHE si il n'y a pas de film dans le fil de discution.

    - route_after_title_check : Analyse le champ 'current_step' pour dispatcher
      le flux de recherche :
        * "direct_movie_detail" (Processus A) : Si un titre explicite et unique est détecté.
        * "filter_and_search_hybrid" (Processus B) : Si la requête nécessite une recherche
          multicritères par filtres (genres, réalisateur, scores, etc.).

================================================================================
PHASE 2 : ROUTAGE D'ÉVALUATION ET DE RÉFLEXION (L'EXPERT)
================================================================================
Supervise les transitions logiques entre la collecte interne de données et l'enrichissement externe.

    - route_after_validation : Arête conditionnelle appelée après l'évaluation de la
      qualité des données locales (Hydratation_node). Elle vérifie la complétude de l'objet :
        * 'MANQUE DES INFOS' -> Bifurcation dynamique vers la branche d'enrichissement Web
          (wikipedia_search_node).
        * 'PASS' -> Validation et envoi direct des données factuelles au Narrateur.

    - route_retry : Gère les boucles de rétroaction et de correction en cas d'échec
      de cohérence (limité à un maximum de 2 tentatives via 'retry_count').

================================================================================
PHASE 3 : CONVERGENCE ET CLÔTURE
================================================================================
S'assure que peu importe le chemin emprunté (RAG local validé, Bypass conversationnel
ou flux Wikipédia condensé par l'agent de synthèse), les transitions convergent
impérativement vers l'Agent Narrateur (nodes.py) avant la sauvegarde finale.

--------------------------------------------------------------------------------
Dépendances principales :
    - api.schemas (AgentState)
    - agents.nodes (Cibles de routage pour le constructeur du graphe)

Auteur/Responsable : Équipe Agents
"""

from api.schemas import AgentState

# LOGGER ------------------------------------------------------
from logger import get_logger, setup_logger

setup_logger()

logger = get_logger("ROUTER")


# ==============================================================================
# ROUTING LOGIC
# ==============================================================================


def route_after_title_check(state: AgentState) -> str:
    """Aiguille le workflow selon la présence ou non d'un titre de film précis."""
    logger.info(
        f"Routage conditionnel invoqué. Étape actuelle détectée : '{state.current_step}'"
    )
    if state.current_step == "has_title":
        logger.info("Aiguillage vers le processus A : 'direct_movie_detail'")
        return "direct_movie_detail"
    logger.info("Aiguillage vers le processus B : 'filter_and_search_hybrid'")
    return "filter_and_search_hybrid"
