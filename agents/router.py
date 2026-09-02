"""agents/router.py
Module de routage conditionnel et d'aiguillage du graphe HorRAGor v3.

Ce fichier centralise exclusivement la logique de transition et les embranchements
dynamiques (Conditional Edges) de la Machine à États Finis (FSM) de l'agent. Il ne
contient aucune implémentation de nœud (exécutée dans nodes.py), garantissant ainsi
une séparation stricte entre la logique de décision de trajectoire et l'exécution.

En se basant sur les variables d'état de l'AgentState, ce module implémente les fonctions
d'aiguillage suivantes à travers les 3 phases du programme :

================================================================================
PHASE 1 : AIGUILLAGE DE L'INTENTION ET DE L'ENTRÉE (LE CERVEAU)
================================================================================
Aiguille le flux dès la réception du message utilisateur pour séparer les requêtes
de recherche lourdes des interactions conversationnelles (Bypass).

    - route_by_intent : Dispatche selon l'intention classifiée par intent_classifier_node :
        * "RECHERCHE"        → route_after_title_check (pipeline RAG complet).
        * "DISCUSSION"       → load_film_node (bypass mémoire session).
        * "CHITCHAT"         → narrator_node (court-circuit direct, pas de BDD).
        * "AUCUN_FILM_TROUVE"→ narrator_node (court-circuit, invite à rechercher).

    - route_after_title_check : Dispatche selon la présence d'un titre explicite :
        * "has_title"  → search_vector_node (Processus A - Direct).
        * "no_title"   → merge_filters_node (Processus B - Hybride).

    - route_verif_film : Valide l'alignement contextuel après load_film_node :
        * retrieved_movies vide ou "intent_rupture" → route_after_title_check.
        * film chargé et cohérent                   → verif_film_node.

================================================================================
PHASE 2 : ROUTAGE DE RECHERCHE & RÉFLEXION (L'EXPERT)
================================================================================
Supervise les transitions entre collecte interne, enrichissement externe et
boucles de rétroaction (max 2 tentatives via retry_count).

    - route_direct_id_valid : Valide la présence d'un film après search_vector_node (Direct).
        * 1 film trouvé    → hydratation_node.
        * 0 film, retry<2  → search_vector_node (RETRY).
        * 0 film, retry>=2 → narrator_node (FAIL).

    - route_hybrid_id_valid : Valide la présence de films après search_vector_node (Hybride).
        * films trouvés    → format_cards_node.
        * 0 film, retry<2  → merge_filters_node (RETRY).
        * 0 film, retry>=2 → narrator_node (FAIL).

    - route_need_wikipedia : Oriente selon branch_search_wiki et current_step :
        * RAG + "valid_missing_synopsis" → wikipedia_search_node.
        * RAG + search_branch="direct"   → card_node.
        * RAG + search_branch="hybrid"   → format_cards_node.
        * DISCUSSION + "valid_missing_data" → wikipedia_search_node.
        * DISCUSSION + données suffisantes  → synthesis_node.

    - route_return_wiki : Convergence post-synthèse Wikipédia :
        * RAG        → card_node ou format_cards_node selon search_branch.
        * DISCUSSION → synthesis_node → narrator_node.

================================================================================
PHASE 3 : ROUTAGE DE VALIDATION (LE GARDIEN)
================================================================================
Évalue la cohérence sémantique des résultats avant génération finale.

    - route_validation_direct : Valide le film hydraté (Processus A) :
        * "valid" ou "valid_missing_synopsis" → route_need_wikipedia (PASS).
        * "invalid_coherence", retry<2        → search_vector_node (RETRY).
        * "invalid_coherence", retry>=2       → narrator_node (FAIL).

    - route_validation_hybrid : Valide la liste de films (Processus B) :
        * "valid"                      → route_need_wikipedia (PASS total).
        * "valid_partial"              → route_need_wikipedia (PASS partiel, liste filtrée).
        * "invalid_coherence", retry<2 → merge_filters_node (RETRY).
        * "invalid_coherence", retry>=2→ narrator_node (FAIL).

--------------------------------------------------------------------------------
Statuts current_step reconnus :
    "has_title"              : titre détecté par title_router_node
    "no_title"               : pas de titre, branche hybride
    "filters_ready"          : filtres SQL consolidés par merge_filters_node
    "has_results"            : films trouvés par search_vector_node
    "no_results"             : aucun film trouvé (pool SQL vide ou FAISS vide)
    "hydrated"               : FilmDetail chargé par hydratation_node
    "card_ready"             : carte prête pour envoi SSE (card_node)
    "cards_ready"            : liste de cartes prête pour envoi SSE (format_cards_node)
    "valid"                  : validation réussie (direct ou hybride)
    "valid_partial"          : validation partielle hybride (liste filtrée)
    "valid_missing_synopsis" : film valide mais synopsis absent (RAG)
    "valid_missing_data"     : film valide mais donnée demandée absente (DISCUSSION)
    "invalid_coherence"      : film ou liste incohérent avec la requête
    "intent_rupture"         : changement de sujet détecté en mode DISCUSSION
    "film_loaded"            : FilmDetail chargé depuis la mémoire session
    "wiki_done"              : enrichissement Wikipedia effectué
    "synthesis_done"         : synthèse LLM produite
    "completed"              : réponse finale générée par narrator_node

Variables d'état clés :
    branch_search_wiki : "RAG" | "DISCUSSION"
    search_branch      : "direct" | "hybrid"
    retry_count        : int (max 2)

Dépendances principales :
    - api.schemas (AgentState)
    - agents.nodes (Cibles de routage pour le constructeur du graphe)

Auteur/Responsable : Équipe Agents - Spécification HorRAGor v3
--------------------------------------------------------------------------------
"""

from shared.schemas import AgentState

# LOGGER ------------------------------------------------------
from logger import get_logger, setup_logger

setup_logger()

logger = get_logger("ROUTER")


# ==============================================================================
# PHASE 1 : ROUTAGE DE L'INTENTION & ENTRÉE (LE CERVEAU)
# ==============================================================================


def route_by_intent(state: AgentState) -> str:
    """
    Évalue l'intention utilisateur pour séparer la recherche du chitchat.

    Returns:
        str: "Load_film_node" (Bypass DISCUSSION) ou "route_after_title_check" (RECHERCHE).
    """
    intent = getattr(state, "intent", "RECHERCHE")
    logger.info(f"[route_by_intent] Intention détectée : '{intent}'")

    # 1. L'utilisateur pose une question sur le film actuellement en mémoire
    if intent == "DISCUSSION":
        logger.info(
            f"[route_by_intent] Routage vers load_film_node pour l'intention : '{intent}'"
        )
        return "Load_film_node"

    # 2. L'utilisateur fait une nouvelle demande ou veut changer de film
    elif intent == "RECHERCHE":
        logger.info(
            f"[route_by_intent] Routage vers route_after_title_check pour l'intention : '{intent}'"
        )
        return "route_after_title_check"

    # 3. Sécurités / Cas aux limites : requêtes vides, mémoires mortes ou politesse.
    # On court-circuite la base de données et on envoie directement au nœud de réponse.
    elif intent in ["AUCUN_FILM_TROUVE", "CHITCHAT"]:
        logger.warning(
            f"[route_by_intent] Court-circuit vers narrator_node pour l'intention : {intent}"
        )
        return "narrator_node"

    # 4. Fallback par défaut par sécurité
    else:
        logger.warning(
            f"[route_by_intent] Fallback vers route_after_title_check pour l'intention : '{intent}'"
        )
        return "route_after_title_check"


def route_after_title_check(state: AgentState) -> str:
    """Aiguille le workflow selon la présence ou non d'un titre de film précis.
    Returns:
        str: "direct_movie_detail" (Processus A : direct) ou "filter_and_search_hybrid" (Processus B : hybride).
    """
    logger.info(
        f"[route_after_title_check] Routage conditionnel invoqué. Étape actuelle détectée : '{state.current_step}'"
    )
    # 1. Vérification de l'existence d'un titre de film direction direction processus A : 'direct_movie_detail'
    if state.current_step == "has_title":
        logger.info(
            "[route_after_title_check] Aiguillage vers le processus A : 'direct_movie_detail'"
        )
        return "direct_movie_detail"

    # 2. Fallback vers le processus B : 'filter_and_search_hybrid'
    else:
        logger.info(
            "[route_after_title_check] Aiguillage vers le processus B : 'filter_and_search_hybrid'"
        )
        return "filter_and_search_hybrid"


def route_verif_film(state: AgentState) -> str:
    """
    Aiguille le workflow après le chargement du film en mémoire (Bypass DISCUSSION).

    Cette arête s'appuie sur la validation sémantique effectuée par le LLM lors du
    nœud précédent (Load_film_node) pour détecter un changement brutal de sujet.

    Returns:
        str: - "route_need_wikipedia" : Si le LLM a validé l'alignement contextuel.
             - "route_after_title_check" : Si aucun film n'est chargé ou si le LLM
               a détecté une rupture d'intention (changement de film).
    """
    logger.info("[route_verif_film] Validation sémantique du contexte...")

    # Lecture du verdict du LLM stocké dans le State
    validation_status = getattr(state, "current_step", "")

    # 1. Vérification technique de sécurité
    if not state.retrieved_movies or len(state.retrieved_movies) == 0:
        logger.warning("[route_verif_film] Aucun film en mémoire. Redirection RAG.")
        return "route_after_title_check"

    # 2. Vérification du verdict du LLM
    elif validation_status == "intent_rupture":
        logger.info(
            "[route_verif_film] Le LLM a détecté un changement de sujet. Redirection vers le pipeline de RECHERCHE."
        )
        return "merge_filters_node"

    # 3. Validation réussie
    else:
        film_courant = state.retrieved_movies[0]
        logger.info(
            f"[route_verif_film] Clé validée par LLM. Poursuite de la discussion sur : '{getattr(film_courant, 'title', 'Inconnu')}'"
        )
        return "route_need_wikipedia"


# ==============================================================================
# PHASE 2 : ROUTAGE DE RECHERCHE & RÉFLEXION (L'EXPERT)
# ==============================================================================


def route_need_wikipedia(state: AgentState) -> str:
    """
    Arête conditionnelle (Phase 2) déterminant la redirection après l'évaluation Wikipédia.

    Cette route pure utilise la variable 'branch_search_wiki' pour orienter le flux :
      - Si elle vaut "RAG" -> Redirection vers le nœud de clôture "end_rag".
      - Si elle vaut "DISCUSSION" -> Redirection vers "wikipedia_search_node" (si infos manquantes)
        ou directement vers "narrator_node".

    Args:
        state (AgentState): L'état actuel du graphe.

    Returns:
        str: Le nom du prochain nœud cible (nodes.py) ou de la prochaine route :
             - "end_rag"
             - "wikipedia_search_node"
             - "narrator_node"
    """
    # Récupération de la provenance (RAG ou DISCUSSION)
    branch = getattr(state, "branch_search_wiki", "RAG")
    status = getattr(state, "current_step", "")
    search_branch = getattr(state, "search_branch", "hybrid")
    logger.info(
        f"[route_need_wikipedia]  Provenance détectée : '{branch}' et {search_branch}"
    )
    logger.info(f"[route_need_wikipedia]  Status détectée : '{status}'")

    # ---------- Cas 1 : Le flux provient du pipeline RAG complet ----------
    if branch == "RAG":
        # 1. Cas particulier : Le LLM a détecté qu'il manquait des informations pour la synthèse finale
        if status == "valid_missing_synopsis":
            logger.info(
                "[route_need_wikipedia]  (Provenance RAG) Direction : wikipedia_search_node."
            )
            return "wikipedia_search_node"

        # 2. Cas branche d'origine direct : Données suffisante,
        elif search_branch == "direct":
            logger.info(
                "[route_need_wikipedia]  (Provenance RAG) Direction : card_node."
            )
            return "card_node"

        # 3. Cas branche d'origine hybrid : Données suffisante,
        else:
            logger.info(
                "[route_need_wikipedia] (Provenance RAG) Direction : card_node."
            )
            return "format_cards_node"

    # ---------- Cas 2 : Le flux provient du bypass DISCUSSION ----------
    if branch == "DISCUSSION":
        # 4. Si le LLM ou le nœud précédent a marqué qu'il manquait des informations nécessaires
        if status == "valid_missing_data":
            logger.info(
                "[route_need_wikipedia]  (Provenance DISCUSSION) Infos manquantes. Direction : wikipedia_search_node."
            )
            return "wikipedia_search_node"

        # 4. Sinon, on peut directement générer la réponse
        else:
            logger.info(
                "[route_need_wikipedia]  (Provenance DISCUSSION) Données suffisantes. Direction : narrator_node."
            )
            return "narrator_node"

    # Cas 3 : Fallback de sécurité par défaut
    else:
        logger.warning(
            f"[route_need_wikipedia] Valeur inattendue pour branch_search_wiki : '{branch}'. Repli sur narrator_node."
        )
        return "narrator_node"


def route_direct_id_valid(state: AgentState) -> str:
    """
    [Processus A - Direct Movie] Valide les résultats de la recherche vectorielle.

    En cas d'absence d'identifiant, initie une boucle de rétroaction (RETRY)
    jusqu'à 2 fois maximum avant de déclarer un échec définitif (FAIL).

    Returns:
        str: - "Hydratation_node" : Si un film correspondant a été trouvé (PASS).
             - "Search_vector_node" : Si aucun film mais retry_count < 2 (RETRY).
             - "Format_Card_node" : Si aucun film et retry_count >= 2 (FAIL).
    """
    logger.info("[route_direct_id_valid] Validation des IDs (Direct)...")

    # ---------- Cas PASS : Des identifiants ont été trouvés ----------
    # 1. Si un seul film a été trouvé, retour sur branche directe
    if state.retrieved_movies and len(state.retrieved_movies) == 1:
        logger.info(
            f"[route_direct_id_valid] (PASS) -> {len(state.retrieved_movies)} film détecté."
        )
        return "Affichage_film_unique"

    # 2. Si un plusieurs films ont été trouvé, retour sur branche hybrid
    elif state.retrieved_movies and len(state.retrieved_movies) > 1:
        logger.info(
            f"[route_direct_id_valid] (PASS) -> {len(state.retrieved_movies)} films détectés."
        )
        return "Affichage_films"

    # ---------- Cas RETRY / FAIL si aucun film n'est trouvé ----------
    retry_count = getattr(state, "retry_count", 0)
    logger.warning(
        f"[route_direct_id_valid] Aucun film trouvé. Compteur de retry actuel : {retry_count}/2"
    )

    # 3. Si le compteur de retry est inférieur à 2, on reboucle vers la recherche vectorielle
    if retry_count < 2:
        logger.info(
            "[route_direct_id_valid] (RETRY) -> Ré-exécution de la recherche vectorielle."
        )
        return "Search_vector_node"

    # 4. Si le compteur de retry est égal ou supérieur à 2, on considère l'échec et on redirige vers le nœud de synthèse
    else:
        logger.error(
            "[route_direct_id_valid] (FAIL) -> Limite de retry atteinte. Direction : Format_Card_node."
        )
        return "narrator_node"


def route_hybrid_id_valid(state: AgentState) -> str:
    """
    [Processus B - Filtres et Search] Valide les résultats de la recherche hybride.

    En cas d'échec de correspondance avec les critères, initie un rebouclage (RETRY)
    vers l'ajustement des filtres (Merge_filters_node) avant abandon (FAIL).

    Returns:
        str: - "Affichage_film_unique" : Si au moins un film candidat a été trouvé (PASS).
             - "Merge_filters_node" : Si aucun film mais retry_count < 2 (RETRY).
             - "Affichage_films" : Si aucun film et retry_count >= 2 (FAIL).
    """
    logger.info("[route_hybrid_id_valid] Validation des IDs (Hybride)...")

    # ---------- Cas PASS : Des identifiants correspondent aux filtres ----------
    # 1. Si un seul film a été trouvé, retour sur branche directe
    if state.retrieved_movies and len(state.retrieved_movies) == 1:
        logger.info(
            f"[route_hybrid_id_valid] (PASS) -> {len(state.retrieved_movies)} film détecté."
        )
        return "Affichage_film_unique"

    # 2. Si un plusieurs films ont été trouvé, retour sur branche hybrid
    elif state.retrieved_movies and len(state.retrieved_movies) > 1:
        logger.info(
            f"[route_hybrid_id_valid] (PASS) -> {len(state.retrieved_movies)} films détectés."
        )
        return "Affichage_films"

    # ---------- Cas RETRY / FAIL si aucun film n'est trouvé ----------
    retry_count = getattr(state, "retry_count", 0)
    logger.warning(
        f"[route_hybrid_id_valid] Aucun film ne correspond aux critères. Compteur : {retry_count}/2"
    )

    # 3. Si le compteur de retry est inférieur à 2, on reboucle vers la le merge_filters_node
    if retry_count < 2:
        logger.info(
            "[route_hybrid_id_valid] (RETRY) -> Rebouclage vers Merge_filters_node pour ajustement."
        )
        return "Merge_filters_node"

    # 4. Si le compteur de retry est égal ou supérieur à 2, on considère l'échec et on redirige vers le nœud de synthèse
    else:
        logger.error(
            "[route_hybrid_id_valid] (FAIL) -> Limite de retry atteinte. Direction : Format_Card_node."
        )
        return "narrator_node"


def route_return_wiki(state: AgentState) -> str:
    """
    [Agent Wiki] Oriente le flux après la synthèse des informations Wikipédia.

    Arête conditionnelle (Phase 2) : utilise la variable de provenance
    'branch_search_wiki' pour renvoyer les données enrichies vers le bon
    point de convergence de l'architecture.

    Args:
        state (AgentState): L'état actuel du graphe contenant les données enrichies.

    Returns:
        str: - "end_rag" : Si l'enrichissement Wikipédia a été déclenché depuis le pipeline RAG.
             - "narrator_node" : Si l'enrichissement a été déclenché depuis le mode DISCUSSION.
    """
    branch = getattr(state, "branch_search_wiki", "RAG")
    logger.info(
        f"[route_return_wiki] Fin de la synthèse Wiki. Provenance initiale : '{branch}'"
    )

    # Cas 1 : L'enrichissement s'est fait au cours du processus RAG (Direct ou Hybride)
    if branch == "RAG":
        logger.info("[route_return_wiki] Retour vers le bloc de clôture RAG : end_rag.")
        return "end_rag"

    # Cas 2 : L'enrichissement s'est fait suite à un manque d'infos dans le mode discussion
    elif branch == "DISCUSSION":
        logger.info(
            "[route_return_wiki] Retour direct vers la plume gothique : narrator_node."
        )
        return "synthesis_node"

    # Cas 3 : Fallback de sécurité par défaut
    else:
        logger.warning(
            f"[route_return_wiki] Provenance inconnue '{branch}'. Sécurité vers narrator_node."
        )
        return "narrator_node"


# ==============================================================================
# PHASE 3 : ROUTAGE DE VALIDATION
# ==============================================================================


def route_validation_direct(state: AgentState) -> str:
    """
    [Processus A - Direct Movie] Évalue la cohérence du film extrait par recherche directe.

    Vérifie si le film unique hydraté correspond précisément à la demande initiale.
    En cas d'incohérence, initie un RETRY vers la recherche ou un FAIL vers le Narrateur.

    Returns:
        str: - "route_need_wikipedia" : Si le film est validé et cohérent (PASS).
             - "Search_vector_node" : Si incohérence et retry_count < 2 (RETRY).
             - "narrator_node" : Si limite atteinte (FAIL -> Excuses).
    """
    logger.info(
        "[route_validation_direct] Évaluation de la pertinence du film direct..."
    )

    status = getattr(state, "current_step", "")

    # 1. Cas PASS : Le film est pertinent
    if status != "invalid_coherence":
        logger.info("[route_validation_direct] (PASS) -> Film validé sémantiquement.")
        return "route_need_wikipedia"

    # Recupération du compteur de Retry
    retry_count = getattr(state, "retry_count", 0)
    logger.warning(
        f"[route_validation_direct] Film jugé incohérent. Compteur : {retry_count}/2"
    )

    # 2. Cas RETRY : le film n'est pas pertinant et le compteur de RETRY est inférieur à 2
    if retry_count < 2:
        logger.info(
            "[route_validation_direct] (RETRY) -> Ré-exécution de Search_vector_node."
        )
        return "Search_vector_node"

    # 3. Cas FAIL : le film n'est pas pertinant et le compteur de RETRY est inférieur à 2
    else:
        logger.error("[route_validation_direct] (FAIL) -> Transfert au Narrateur.")
        return "narrator_node"


def route_validation_hybrid(state: AgentState) -> str:
    """
    [Processus B - Filtres et Search] Évalue la cohérence des films par rapport aux filtres.

    Vérifie si la liste de films issue de la recherche hybride répond aux critères.
    En cas d'incohérence, reboucle sur la correction des filtres (Merge_filters_node).

    Returns:
        str: - "route_need_wikipedia" : Si la sélection est cohérente (PASS).
             - "Merge_filters_node" : Si incohérence et retry_count < 2 (RETRY).
             - "narrator_node" : Si limite de retry atteinte (FAIL -> Excuses).
    """
    logger.info(
        "[route_validation_hybrid] Évaluation de la cohérence de la liste de films..."
    )

    status = getattr(state, "current_step", "")

    # 1. Cas PASS : La liste de films respecte les filtres et l'intention
    if status == "valid":
        logger.info("[route_validation_hybrid] (PASS) -> Liste de films validée.")
        return "route_need_wikipedia"

    # 1. Cas PASS PARTIEL : Une partie de la liste de films respecte les filtres et l'intention
    elif status == "valid_partial":
        logger.info(
            "[route_validation_hybrid] (PASS PARTIEL) -> Liste de films validée."
        )
        return "route_need_wikipedia"

    # Recupération du compteur de Retry
    retry_count = getattr(state, "retry_count", 0)
    logger.warning(
        f"[route_validation_hybrid] Sélection incohérente. Compteur : {retry_count}/2"
    )

    # 2. Cas RETRY : les films ne sont pas pertinant et le compteur de RETRY est inférieur à 2
    if retry_count < 2:
        logger.info(
            "[route_validation_hybrid] (RETRY) -> Rebouclage vers Merge_filters_node pour ajustement."
        )
        return "Merge_filters_node"

    # 3. Cas FAIL : les films ne sont pas pertinant et le compteur de RETRY est inférieur à 2
    else:
        logger.error("[Rouroute_validation_hybridte] (FAIL) -> Transfert au Narrateur.")
        return "narrator_node"
