"""tests/test_nodes_narrateur.py"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from agents.nodes_narrateur import narrator_node
from api.schemas import AgentStep

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def base_state():
    """État minimal par défaut."""
    state = MagicMock()
    state.user_query = "test query"
    state.intent = "RECHERCHE"
    state.current_step = "card_ready"
    state.data_enriched = ""
    state.retrieved_movies = []
    state.last_displayed_movies_id = []
    state.steps = []
    return state


class MockFilmDetail:
    def __init__(self, tmdb_id=123, title="Alien"):
        self.tmdb_id = tmdb_id
        self.title = title
        self.realisateur = "Ridley Scott"
        self.director = "Ridley Scott"
        self.release_date = "1979-05-25"
        self.runtime = 117
        self.genres = ["Horror", "Science Fiction"]
        self.synopsis = "A terrifying creature in space."
        self.tagline = "In space no one can hear you scream."
        self.tmdb_score = 8.2
        self.imdb_score = 8.1
        self.rotten_tomatometer = 98
        self.collection = None


# ==============================================================================
# CAS A : CHITCHAT
# ==============================================================================


@patch("agents.nodes_narrateur.llm_narrateur")
def test_narrator_cas_a_chitchat(mock_llm, base_state):
    """
    Cas A : intent=CHITCHAT → réponse de bienvenue gothique.
    Le LLM reçoit un contexte d'accueil et retourne une réponse.
    """
    base_state.intent = "CHITCHAT"
    base_state.user_query = "bonjour"
    mock_llm.invoke.return_value = AIMessage(
        content="Bienvenue dans mon manoir sombre..."
    )

    result = narrator_node(base_state)

    assert result["answer"] == "Bienvenue dans mon manoir sombre..."
    assert result["current_step"] == "completed"
    assert any(s.step == "narrator" for s in result["steps"])
    # Vérifie que le contexte chitchat est bien passé au LLM
    call_args = mock_llm.invoke.call_args[0][0]
    assert any("conversation légère" in str(m.content) for m in call_args)


# ==============================================================================
# CAS B : AUCUN_FILM_TROUVE
# ==============================================================================


@patch("agents.nodes_narrateur.llm_narrateur")
def test_narrator_cas_b_aucun_film_trouve(mock_llm, base_state):
    """
    Cas B : intent=AUCUN_FILM_TROUVE → message d'excuse gothique.
    """
    base_state.intent = "AUCUN_FILM_TROUVE"
    base_state.retrieved_movies = []
    mock_llm.invoke.return_value = AIMessage(content="Les cryptes restent scellées...")

    result = narrator_node(base_state)

    assert result["answer"] == "Les cryptes restent scellées..."
    assert result["current_step"] == "completed"
    call_args = mock_llm.invoke.call_args[0][0]
    assert any("échoué" in str(m.content) for m in call_args)


@patch("agents.nodes_narrateur.llm_narrateur")
def test_narrator_cas_b_invalid_coherence(mock_llm, base_state):
    """
    Cas B : current_step=invalid_coherence → même chemin qu'AUCUN_FILM_TROUVE.
    """
    base_state.intent = "RECHERCHE"
    base_state.current_step = "invalid_coherence"
    base_state.retrieved_movies = []
    mock_llm.invoke.return_value = AIMessage(
        content="Le brouillard a englouti les archives..."
    )

    result = narrator_node(base_state)

    assert result["current_step"] == "completed"
    call_args = mock_llm.invoke.call_args[0][0]
    assert any("échoué" in str(m.content) for m in call_args)


@patch("agents.nodes_narrateur.llm_narrateur")
def test_narrator_cas_b_retrieved_movies_vide(mock_llm, base_state):
    """
    Cas B : retrieved_movies vide même avec intent=RECHERCHE → chemin B.
    """
    base_state.intent = "RECHERCHE"
    base_state.current_step = "completed"
    base_state.retrieved_movies = []
    mock_llm.invoke.return_value = AIMessage(content="Aucun film dans les archives...")

    result = narrator_node(base_state)

    call_args = mock_llm.invoke.call_args[0][0]
    assert any("échoué" in str(m.content) for m in call_args)


# ==============================================================================
# CAS C : RECHERCHE NOMINALE (card_ready / cards_ready)
# ==============================================================================


@patch("agents.nodes_narrateur.llm_narrateur")
def test_narrator_cas_c_card_ready(mock_llm, base_state):
    """
    Cas C : current_step=card_ready → introduction gothique des cartes.
    Le contexte mentionne les titres des films trouvés.
    (L'hydratation de last_displayed_movies_id est gérée par le nœud card en amont).
    """
    film = MockFilmDetail()
    base_state.current_step = "card_ready"
    base_state.retrieved_movies = [film]

    # On simule que le nœud "card" a déjà extrait et stocké l'identifiant
    base_state.last_displayed_movies_id = [123]

    mock_llm.invoke.return_value = AIMessage(content="Les parchemins révèlent Alien...")

    result = narrator_node(base_state)

    # Vérifications des responsabilités réelles du narrateur
    assert result["answer"] == "Les parchemins révèlent Alien..."
    assert result["current_step"] == "completed"

    call_args = mock_llm.invoke.call_args[0][0]
    assert any("Alien" in str(m.content) for m in call_args)

    # Vérification optionnelle : on s'assure que le narrateur ne détruit pas la mémoire
    assert result["last_displayed_movies_id"] == [123]


@patch("agents.nodes_narrateur.llm_narrateur")
def test_narrator_cas_c_cards_ready(mock_llm, base_state):
    """
    Cas C : current_step=cards_ready → même chemin que card_ready.
    (L'hydratation de last_displayed_movies_id est gérée par les nœuds card)
    """
    films = [MockFilmDetail(tmdb_id=i, title=f"Film {i}") for i in range(1, 4)]
    base_state.current_step = "cards_ready"
    base_state.retrieved_movies = films

    # Optionnel : On simule que le nœud "card" (passé juste avant) a bien fait son travail
    base_state.last_displayed_movies_id = [1, 2, 3]

    mock_llm.invoke.return_value = AIMessage(
        content="Trois reliques émergent des ténèbres..."
    )

    result = narrator_node(base_state)

    # On vérifie que le narrateur fait bien son travail spécifique
    assert result["answer"] == "Trois reliques émergent des ténèbres..."

    # On vérifie que l'appel au LLM s'est bien fait avec le bon contexte
    call_args = mock_llm.invoke.call_args[0][0]
    assert any("parchemins" in str(m.content) for m in call_args)

    # Si votre nœud narrateur renvoie l'état complet, on s'assure qu'il n'a pas altéré la mémoire.
    # S'il ne renvoie que les clés modifiées (ex: {"answer": ...}), vous pouvez omettre cette ligne.
    assert result["last_displayed_movies_id"] == [1, 2, 3]


# ==============================================================================
# CAS D : DISCUSSION (synthèse factuelle)
# ==============================================================================


@patch("agents.nodes_narrateur.llm_narrateur")
def test_narrator_cas_d_discussion_avec_data_enriched(mock_llm, base_state):
    """
    Cas D : DISCUSSION avec data_enriched fourni par verif_film_node.
    Le narrateur emballe la synthèse factuelle dans un style gothique.
    (La gestion de la mémoire last_displayed_movies_id est faite en amont).
    """
    film = MockFilmDetail()
    base_state.intent = "DISCUSSION"
    base_state.current_step = "synthesis_done"
    base_state.retrieved_movies = [film]
    base_state.data_enriched = "La durée du film 'Alien' est de 117 minutes."

    # On simule la mémoire correctement remplie par un nœud précédent
    base_state.last_displayed_movies_id = [123]

    mock_llm.invoke.return_value = AIMessage(
        content="117 minutes d'angoisse cosmique..."
    )

    result = narrator_node(base_state)

    assert result["answer"] == "117 minutes d'angoisse cosmique..."
    assert result["current_step"] == "completed"

    call_args = mock_llm.invoke.call_args[0][0]
    assert any("117 minutes" in str(m.content) for m in call_args)

    # Vérification conditionnelle pour s'assurer que la mémoire reste intacte
    assert result["last_displayed_movies_id"] == [123]


@patch("agents.nodes_narrateur.llm_narrateur")
def test_narrator_cas_d_discussion_sans_data_enriched(mock_llm, base_state):
    """
    Cas D : DISCUSSION sans data_enriched → utilise film_data_summary directement.
    """
    film = MockFilmDetail()
    base_state.intent = "DISCUSSION"
    base_state.current_step = "synthesis_done"
    base_state.retrieved_movies = [film]
    base_state.data_enriched = None
    mock_llm.invoke.return_value = AIMessage(
        content="Ridley Scott, maître des ténèbres..."
    )

    result = narrator_node(base_state)

    assert result["current_step"] == "completed"
    call_args = mock_llm.invoke.call_args[0][0]
    # Vérifie que les données du film sont dans le contexte
    assert any("Alien" in str(m.content) for m in call_args)
    assert any("117" in str(m.content) for m in call_args)


# ==============================================================================
# MÉMOIRE SESSION : last_displayed_movies_id
# ==============================================================================


@patch("agents.nodes_narrateur.llm_narrateur")
def test_narrator_last_displayed_ids_fallback(mock_llm, base_state):
    """
    Vérifie que last_displayed_movies_id conserve l'ancienne valeur
    si retrieved_movies est vide (cas B).
    """
    base_state.intent = "AUCUN_FILM_TROUVE"
    base_state.retrieved_movies = []
    base_state.last_displayed_movies_id = [999]
    mock_llm.invoke.return_value = AIMessage(content="...")

    result = narrator_node(base_state)

    assert result["last_displayed_movies_id"] == [999]


# ==============================================================================
# FALLBACK LLM
# ==============================================================================


@patch("agents.nodes_narrateur.llm_narrateur")
def test_narrator_fallback_llm_error(mock_llm, base_state):
    """
    Vérifie le fallback textuel si llm_narrateur plante.
    Le nœud ne doit pas lever d'exception et retourner data_enriched ou le message par défaut.
    """
    base_state.current_step = "card_ready"
    base_state.retrieved_movies = [MockFilmDetail()]
    base_state.data_enriched = "Synopsis de secours."
    mock_llm.invoke.side_effect = Exception("Ollama unreachable")

    result = narrator_node(base_state)

    assert result["current_step"] == "completed"
    assert result["answer"] == "Synopsis de secours."
    assert any(s.step == "narrator" for s in result["steps"])


@patch("agents.nodes_narrateur.llm_narrateur")
def test_narrator_fallback_llm_error_sans_data_enriched(mock_llm, base_state):
    """
    Fallback ultime si llm_narrateur plante ET data_enriched est vide.
    """
    base_state.current_step = "card_ready"
    base_state.retrieved_movies = [MockFilmDetail()]
    base_state.data_enriched = ""
    mock_llm.invoke.side_effect = Exception("Ollama unreachable")

    result = narrator_node(base_state)

    assert result["answer"] == "Le silence des tombes s'abat sur votre demande..."


# ==============================================================================
# NETTOYAGE DES BALISES
# ==============================================================================


@patch("agents.nodes_narrateur.llm_narrateur")
def test_narrator_nettoyage_balises_gothiques(mock_llm, base_state):
    """
    Vérifie que les balises <reponse_gothique> sont supprimées du résultat final.
    """
    base_state.current_step = "card_ready"
    base_state.retrieved_movies = [MockFilmDetail()]
    mock_llm.invoke.return_value = AIMessage(
        content="<reponse_gothique>Dans les ténèbres...</reponse_gothique>"
    )

    result = narrator_node(base_state)

    assert "<reponse_gothique>" not in result["answer"]
    assert "</reponse_gothique>" not in result["answer"]
    assert result["answer"] == "Dans les ténèbres..."


# ==============================================================================
# STEPS
# ==============================================================================


@patch("agents.nodes_narrateur.llm_narrateur")
def test_narrator_steps_append(mock_llm, base_state):
    """
    Vérifie que narrator ajoute bien un AgentStep au pipeline.
    """
    base_state.steps = [AgentStep(step="card", status="Carte prête")]
    base_state.current_step = "card_ready"
    base_state.retrieved_movies = [MockFilmDetail()]
    mock_llm.invoke.return_value = AIMessage(content="...")

    result = narrator_node(base_state)

    assert len(result["steps"]) == 2
    assert result["steps"][-1].step == "narrator"


@patch("agents.nodes_narrateur.llm_narrateur")
def test_narrator_cas_c_multi_films_contexte(mock_llm, base_state):
    """
    Cas C : cards_ready avec plusieurs films — vérifie que TOUS les titres
    sont présents dans le contexte LLM, pas seulement le premier.
    """
    films = [
        MockFilmDetail(tmdb_id=1, title="Alien"),
        MockFilmDetail(tmdb_id=2, title="The Shining"),
        MockFilmDetail(tmdb_id=3, title="Halloween"),
    ]
    base_state.current_step = "cards_ready"
    base_state.retrieved_movies = films
    base_state.last_displayed_movies_id = [1, 2, 3]
    mock_llm.invoke.return_value = AIMessage(content="Trois monstres émergent...")

    result = narrator_node(base_state)

    call_args = mock_llm.invoke.call_args[0][0]
    context_str = " ".join(str(m.content) for m in call_args)
    assert "Alien" in context_str
    assert "The Shining" in context_str
    assert "Halloween" in context_str


@patch("agents.nodes_narrateur.llm_narrateur")
def test_narrator_cas_d_film_sans_attributs_optionnels(mock_llm, base_state):
    """
    Cas D : Film avec attributs manquants (None) — vérifie que getattr défensif
    ne lève pas d'exception et produit 'Non disponible'.
    """
    film = MagicMock()
    film.tmdb_id = 42
    film.title = "Film Incomplet"
    film.realisateur = None
    film.director = None
    film.release_date = None
    film.runtime = None
    film.genres = None
    film.synopsis = None
    film.tagline = None
    film.tmdb_score = None
    film.imdb_score = None
    film.rotten_tomatometer = None
    film.collection = None

    base_state.intent = "DISCUSSION"
    base_state.current_step = "synthesis_done"
    base_state.retrieved_movies = [film]
    base_state.data_enriched = ""
    base_state.last_displayed_movies_id = [42]
    mock_llm.invoke.return_value = AIMessage(content="Réponse gothique...")

    result = narrator_node(base_state)

    assert result["current_step"] == "completed"
    assert result["answer"] == "Réponse gothique..."
    call_args = mock_llm.invoke.call_args[0][0]
    assert any("Non disponible" in str(m.content) for m in call_args)


@patch("agents.nodes_narrateur.llm_narrateur")
def test_narrator_cas_b_priorite_sur_cas_c(mock_llm, base_state):
    """
    Cas B > Cas C : si intent=AUCUN_FILM_TROUVE ET retrieved_movies non vide,
    le Cas B doit primer (intent check avant current_step check).
    """
    base_state.intent = "AUCUN_FILM_TROUVE"
    base_state.current_step = "card_ready"  # Cas C normalement
    base_state.retrieved_movies = [MockFilmDetail()]  # Non vide
    mock_llm.invoke.return_value = AIMessage(content="Réponse B...")

    result = narrator_node(base_state)

    call_args = mock_llm.invoke.call_args[0][0]
    # Doit partir sur le contexte B (échec), pas C (cartes)
    assert any("échoué" in str(m.content) for m in call_args)


@patch("agents.nodes_narrateur.llm_narrateur")
def test_narrator_nettoyage_balises_partielles(mock_llm, base_state):
    """
    Vérifie le nettoyage si une seule balise est présente (ouvrante sans fermante).
    """
    base_state.current_step = "card_ready"
    base_state.retrieved_movies = [MockFilmDetail()]
    mock_llm.invoke.return_value = AIMessage(
        content="<reponse_gothique>Dans les ténèbres sans fermeture"
    )

    result = narrator_node(base_state)

    assert "<reponse_gothique>" not in result["answer"]
    assert result["answer"] == "Dans les ténèbres sans fermeture"


@patch("agents.nodes_narrateur.llm_narrateur")
def test_narrator_steps_conserves_depuis_etat_precedent(mock_llm, base_state):
    """
    Vérifie que les steps existants dans le state sont conservés
    et que le step narrator est ajouté en fin de liste, pas en remplacement.
    """
    existing_steps = [
        AgentStep(step="search_vector", status="1 film trouvé"),
        AgentStep(step="validation_direct", status="valid"),
        AgentStep(step="card", status="Carte prête : 'Alien'"),
    ]
    base_state.steps = existing_steps
    base_state.current_step = "card_ready"
    base_state.retrieved_movies = [MockFilmDetail()]
    mock_llm.invoke.return_value = AIMessage(content="...")

    result = narrator_node(base_state)

    assert len(result["steps"]) == 4
    assert result["steps"][0].step == "search_vector"
    assert result["steps"][1].step == "validation_direct"
    assert result["steps"][2].step == "card"
    assert result["steps"][3].step == "narrator"


@patch("agents.nodes_narrateur.llm_narrateur")
def test_narrator_reponse_llm_vide(mock_llm, base_state):
    """
    Vérifie le comportement si le LLM retourne une réponse vide.
    Le strip() ne doit pas lever d'exception.
    """
    base_state.current_step = "card_ready"
    base_state.retrieved_movies = [MockFilmDetail()]
    mock_llm.invoke.return_value = AIMessage(content="")

    result = narrator_node(base_state)

    assert result["current_step"] == "completed"
    assert result["answer"] == ""
