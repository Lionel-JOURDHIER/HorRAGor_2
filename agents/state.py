"""agents/state.py
Module de définition de l'état (State) du graphe transactionnel de LangGraph.

Ce fichier définit la structure de données centrale ('AgentState') qui circule
et évolue de nœud en nœud tout au long du cycle de réflexion de l'agent. Il sert
de mémoire de travail pour stocker l'historique et les variables intermédiaires.

Attributs clés de l'état (State) :
    - messages : Annotated[list, add_messages] -> Historique de la conversation.
    - user_filters : Dict -> Contient les filtres natifs du formulaire envoyés par l'API
                     (Réalisateur, Genres à conserver/exclure, limites d'années [1900-2026],
                     score TMDB [0-10], durées [1-685 min]).
    - node_extraction_overrides : Dict -> Filtres optionnels supplémentaires si le LLM
                                  détecte des critères parlés en plus dans le texte du chat.
    - films_pool : List[Dict] -> Buffet de films qualifiés par les outils SQL/FAISS avant filtrage final.

Dépendances principales :
    - typing (TypedDict, Annotated)
    - langgraph.graph.message (add_messages)
"""
