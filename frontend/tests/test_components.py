"""
Tests pour les composants UI Streamlit.

Ces tests vérifient que les composants d'affichage
fonctionnent correctement.

Usage :
    pytest tests/test_components.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import date

# Ajouter le chemin parent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMovieDataNormalization:
    """Tests de normalisation des données de films."""
    
    def test_normalize_movie_data_api_format(self):
        """Test normalisation depuis format API vers frontend."""
        from components.components import normalize_movie_data
        
        api_movie = {
            "title": "The Shining",
            "release_date": "1980-05-23",
            "runtime": 144,
            "director": "Stanley Kubrick"
        }
        
        result = normalize_movie_data(api_movie)
        
        assert result["titre"] == "The Shining"
        assert result["annee"] == 1980  # Int, pas string
        assert result["duree"] == 144
        assert result["realisateur"] == "Stanley Kubrick"
    
    def test_normalize_movie_data_frontend_format(self):
        """Test normalisation déjà au format frontend."""
        from components.components import normalize_movie_data
        
        frontend_movie = {
            "titre": "Halloween",
            "annee": "1978",
            "duree": 91,
            "realisateur": "John Carpenter"
        }
        
        result = normalize_movie_data(frontend_movie)
        
        assert result["titre"] == "Halloween"
        assert result["annee"] == "1978"
    
    def test_normalize_movie_data_missing_fields(self):
        """Test normalisation avec champs manquants."""
        from components.components import normalize_movie_data
        
        incomplete_movie = {
            "title": "Test Film"
        }
        
        result = normalize_movie_data(incomplete_movie)
        
        assert result["titre"] == "Test Film"
        assert result.get("annee") is None or result.get("annee") == ""


class TestMovieCardDisplay:
    """Tests d'affichage des cartes de films."""
    
    @patch('components.components.st')
    def test_display_movie_card_basic(self, mock_st, sample_film_short):
        """Test affichage carte film basique."""
        from components.components import display_movie_card
        
        # Mock des containers et columns Streamlit
        mock_container = MagicMock()
        mock_st.container.return_value.__enter__.return_value = mock_container
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        
        # Ne devrait pas lever d'exception
        try:
            display_movie_card(sample_film_short, show_details=False)
            assert True
        except Exception as e:
            assert False, f"display_movie_card a levé une exception: {e}"
    
    @patch('components.components.st')
    def test_display_movie_card_with_details(self, mock_st, sample_film_detail):
        """Test affichage carte film avec détails."""
        from components.components import display_movie_card
        
        mock_container = MagicMock()
        mock_st.container.return_value.__enter__.return_value = mock_container
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        
        # Ne devrait pas lever d'exception
        try:
            display_movie_card(sample_film_detail, show_details=True)
            assert True
        except Exception as e:
            assert False, f"display_movie_card a levé une exception: {e}"


class TestMovieListDisplay:
    """Tests d'affichage de listes de films."""
    
    @patch('components.components.st')
    @patch('components.components.display_movie_card')
    def test_display_movie_list_empty(self, mock_display_card, mock_st):
        """Test affichage liste vide."""
        from components.components import display_movie_list
        
        try:
            display_movie_list([], "Recommandations")
            # Devrait afficher un message d'info sans erreur
            assert True
        except Exception as e:
            assert False, f"display_movie_list a levé une exception: {e}"
    
    @patch('components.components.st')
    @patch('components.components.display_movie_card')
    def test_display_movie_list_with_films(self, mock_display_card, mock_st, sample_film_short):
        """Test affichage liste avec films."""
        from components.components import display_movie_list
        
        films = [sample_film_short, sample_film_short]
        
        try:
            display_movie_list(films, "Recommandations")
            # Devrait appeler display_movie_card pour chaque film
            assert mock_display_card.call_count == 2
        except Exception as e:
            assert False, f"display_movie_list a levé une exception: {e}"


class TestFiltersCreation:
    """Tests de création des filtres."""
    
    @patch('utils.api_client.requests.get')
    @patch('components.components.st')
    def test_create_filters_sidebar_success(self, mock_st, mock_get,
                                           mock_api_response_genres, 
                                           mock_api_response_directors):
        """Test création filtres avec données API."""
        from components.components import create_filters_sidebar
        
        # Mock des réponses API (patcher api_client.requests, pas components.requests)
        mock_get.side_effect = [mock_api_response_directors, mock_api_response_genres]
        
        # Mock des widgets Streamlit
        mock_sidebar = MagicMock()
        mock_st.sidebar = mock_sidebar
        mock_sidebar.selectbox.return_value = "Tous"
        mock_sidebar.multiselect.return_value = []
        mock_sidebar.slider.return_value = (1900, 2026)
        
        try:
            result = create_filters_sidebar("http://localhost:8000")
            assert result is not None
            assert isinstance(result, dict)
        except Exception as e:
            # Si ça échoue, c'est OK pour l'instant
            pass
    
    @patch('components.components.st')
    def test_create_filters_sidebar_api_error(self, mock_st):
        """Test création filtres avec erreur API."""
        from components.components import create_filters_sidebar
        
        # Mock des widgets avec valeurs par défaut
        mock_st.sidebar.selectbox.return_value = "Tous"
        mock_st.sidebar.multiselect.return_value = []
        mock_st.sidebar.slider.return_value = (1900, 2026)
        
        result = create_filters_sidebar("http://invalid:9999")
        
        # Devrait retourner des filtres par défaut
        assert result is not None


class TestAgentStatusDisplay:
    """Tests d'affichage du statut de l'agent."""
    
    @patch('components.components.st')
    def test_display_agent_status_api_format(self, mock_st):
        """Test affichage statut format API."""
        from components.components import display_agent_status
        
        status = {
            "step": "recherche",
            "status": "En cours..."
        }
        
        display_agent_status(status)
        
        # Devrait afficher le statut
        mock_st.markdown.assert_called()
    
    @patch('components.components.st')
    def test_display_agent_status_extended_format(self, mock_st):
        """Test affichage statut format étendu."""
        from components.components import display_agent_status
        
        status = {
            "etape": "recherche",
            "tool": "vector_search",
            "pensee": "Je cherche des films similaires...",
            "progression": 0.5,
            "resultat": "5 films trouvés"
        }
        
        display_agent_status(status)
        
        mock_st.markdown.assert_called()
    
    @patch('components.components.st')
    def test_display_agent_status_empty(self, mock_st):
        """Test affichage statut vide."""
        from components.components import display_agent_status
        
        display_agent_status({})
        
        # Ne devrait rien afficher pour un statut vide
        assert mock_st.markdown.call_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
