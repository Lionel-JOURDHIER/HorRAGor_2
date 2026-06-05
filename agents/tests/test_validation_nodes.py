"""tests/test_validation_nodes.py
Tests unitaires pour la logique de validation, de routage et d'enrichissement.
"""

import unittest
from unittest.mock import MagicMock, patch

from agents.nodes import (
    ValidationResult,
    route_after_validation,
    validation_node,
    wikipedia_enrich_node,
)

# Ajuste les imports selon la structure réelle de tes répertoires
from agents.state import AgentState


# Mock d'un objet Movie pour simuler state.retrieved_movies
class DummyMovie:
    def __init__(self, title: str, tmdb_score: float):
        self.title = title
        self.tmdb_score = tmdb_score


class TestValidationAndEnrichment(unittest.TestCase):
    def setUp(self):
        # Configuration d'un état de base propre pour chaque test
        self.base_state = AgentState(
            user_query="Est-ce que Alien est bien ?",
            current_step="has_title",
            retrieved_movies=[DummyMovie("Alien", 8.5)],
            answer="Alien est un excellent film de Ridley Scott.",
            steps=[],
        )

    # ==========================================================================
    # TESTS POUR : validation_node
    # ==========================================================================

    @patch("agents.nodes.logger")
    def test_validation_node_no_movies(self, mock_logger):
        """Règle 3 : Si retrieved_movies est vide, retour immédiat vers go_to_end."""
        state = self.base_state.model_copy(update={"retrieved_movies": []})

        result = validation_node(state)

        self.assertEqual(result["current_step"], "go_to_end")
        self.assertEqual(len(result["steps"]), 1)
        self.assertIn("Aucun film trouvé", result["steps"][0].status)

    @patch("agents.nodes.structured_llm")
    def test_validation_node_perfect_answer(self, mock_structured_llm):
        """Cas nominal : Réponse pertinente et complète (is_relevant=True, has_missing_info=False)."""
        # Mock de l'évaluateur structuré pour renvoyer un succès
        mock_evaluator = MagicMock()
        mock_evaluator.invoke.return_value = ValidationResult(
            is_relevant=True, has_missing_info=False, feedback="Parfait"
        )
        mock_structured_llm.with_structured_output.return_value = mock_evaluator

        result = validation_node(self.base_state)

        self.assertEqual(result["current_step"], "go_to_end")
        self.assertEqual(result["steps"][-1].status, "Réponse validée à 100%.")

    @patch("agents.nodes.structured_llm")
    def test_validation_node_missing_synopsis(self, mock_structured_llm):
        """Règle 4 : Réponse pertinente mais manque d'informations (has_missing_info=True)."""
        mock_evaluator = MagicMock()
        mock_evaluator.invoke.return_value = ValidationResult(
            is_relevant=True, has_missing_info=True, feedback="Pas de synopsis"
        )
        mock_structured_llm.with_structured_output.return_value = mock_evaluator

        result = validation_node(self.base_state)

        self.assertEqual(result["current_step"], "enrich_with_wiki")
        self.assertIn("Synopsis manquant", result["steps"][-1].status)

    @patch("agents.nodes.structured_llm")
    def test_validation_node_failed_retry_direct(self, mock_structured_llm):
        """Règle 1 : Réponse KO venant de la branche directe (has_title) -> retry_direct."""
        mock_evaluator = MagicMock()
        mock_evaluator.invoke.return_value = ValidationResult(
            is_relevant=False, has_missing_info=False, feedback="Hallucination détectée"
        )
        mock_structured_llm.with_structured_output.return_value = mock_evaluator

        # L'état initial est déjà configuré sur current_step="has_title"
        result = validation_node(self.base_state)

        self.assertEqual(result["current_step"], "retry_direct")
        self.assertIn("Ré-essai de la branche directe", result["steps"][-1].status)

    @patch("agents.nodes.structured_llm")
    def test_validation_node_failed_retry_hybrid(self, mock_structured_llm):
        """Règle 2 : Réponse KO venant de la branche critères (no_title) -> retry_hybrid."""
        mock_evaluator = MagicMock()
        mock_evaluator.invoke.return_value = ValidationResult(
            is_relevant=False, has_missing_info=False, feedback="Hors sujet"
        )
        mock_structured_llm.with_structured_output.return_value = mock_evaluator

        # Modification du step pour simuler la provenance de la branche critères
        state = self.base_state.model_copy(update={"current_step": "no_title"})
        result = validation_node(state)

        self.assertEqual(result["current_step"], "retry_hybrid")
        self.assertIn("Ré-essai de la branche hybride", result["steps"][-1].status)

    @patch("agents.nodes.structured_llm")
    def test_validation_node_exception_fallback(self, mock_structured_llm):
        """Test de la robustesse si le LLM d'évaluation plante -> Doit fallback en True."""
        mock_evaluator = MagicMock()
        mock_evaluator.invoke.side_effect = Exception("API Error")
        mock_structured_llm.with_structured_output.return_value = mock_evaluator

        result = validation_node(self.base_state)

        # Le bloc except force is_relevant=True et has_missing_info=False -> go_to_end
        self.assertEqual(result["current_step"], "go_to_end")

    # ==========================================================================
    # TESTS POUR : route_after_validation
    # ==========================================================================

    def test_route_after_validation_paths(self):
        """Vérifie que chaque clé d'aiguillage renvoie la bonne chaîne pour LangGraph."""
        state_end = self.base_state.model_copy(update={"current_step": "go_to_end"})
        state_wiki = self.base_state.model_copy(
            update={"current_step": "enrich_with_wiki"}
        )
        state_direct = self.base_state.model_copy(
            update={"current_step": "retry_direct"}
        )
        state_hybrid = self.base_state.model_copy(
            update={"current_step": "retry_hybrid"}
        )

        self.assertEqual(route_after_validation(state_end), "go_to_end")
        self.assertEqual(route_after_validation(state_wiki), "enrich_with_wiki")
        self.assertEqual(route_after_validation(state_direct), "retry_direct")
        self.assertEqual(route_after_validation(state_hybrid), "retry_hybrid")

    # ==========================================================================
    # TESTS POUR : wikipedia_enrich_node
    # ==========================================================================

    @patch("agents.nodes.llm")
    @patch("agents.nodes.wikipedia_search")
    def test_wikipedia_enrich_node_success(self, mock_wiki_search, mock_llm):
        """Vérifie l'enrichissement nominal lorsque Wikipédia trouve un résumé."""
        # Config des mocks
        mock_wiki_search.invoke.return_value = {
            "source": "WIKIPEDIA",
            "summary": "Un xénomorphe sème la terreur dans le Nostromo.",
            "url": "https://fr.wikipedia.org/wiki/Alien",
        }

        mock_llm_response = MagicMock()
        mock_llm_response.content = "Réponse finale reconstruite avec le wiki."
        mock_llm.invoke.return_value = mock_llm_response

        result = wikipedia_enrich_node(self.base_state)

        self.assertEqual(result["current_step"], "completed")
        self.assertEqual(result["answer"], "Réponse finale reconstruite avec le wiki.")
        self.assertIn("Synopsis enrichi depuis Wikipédia", result["steps"][-1].status)

    @patch("agents.nodes.llm")
    @patch("agents.nodes.wikipedia_search")
    def test_wikipedia_enrich_node_not_found(self, mock_wiki_search, mock_llm):
        """Vérifie le comportement de secours si Wikipédia ne trouve rien."""
        mock_wiki_search.invoke.return_value = {"source": "NOT_FOUND"}

        mock_llm_response = MagicMock()
        mock_llm_response.content = "Réponse standard sans enrichissement."
        mock_llm.invoke.return_value = mock_llm_response

        result = wikipedia_enrich_node(self.base_state)

        self.assertEqual(result["current_step"], "completed")
        self.assertIn(
            "Aucun complément trouvé sur Wikipédia", result["steps"][-1].status
        )


if __name__ == "__main__":
    unittest.main()
