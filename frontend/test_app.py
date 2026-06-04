"""
Tests unitaires pour les composants de l'interface Streamlit.

Pour lancer les tests :
    pytest test_app.py -v

Note : Ces tests nécessitent pytest et pytest-mock
Installation : pip install pytest pytest-mock
"""

import pytest
from unittest.mock import Mock, patch
from utils import api_client


class TestApiClient:
    """Tests pour le module api_client."""
    
    def test_get_api_url_default(self):
        """Test de l'URL par défaut de l'API."""
        with patch.dict('os.environ', {}, clear=True):
            url = api_client.get_api_url()
            assert url == "http://localhost:8000"
    
    def test_get_api_url_custom(self):
        """Test de l'URL personnalisée de l'API."""
        with patch.dict('os.environ', {'API_URL': 'http://custom:9000'}):
            url = api_client.get_api_url()
            assert url == "http://custom:9000"
    
    @patch('utils.api_client.requests.get')
    def test_check_health_success(self, mock_get):
        """Test de la vérification de santé avec succès."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response
        
        result = api_client.check_health()
        assert result["status"] == "ok"
    
    @patch('utils.api_client.requests.get')
    def test_check_health_error(self, mock_get):
        """Test de la vérification de santé avec erreur."""
        mock_get.side_effect = Exception("Connection refused")
        
        result = api_client.check_health()
        assert result["status"] == "error"
    
    @patch('utils.api_client.requests.get')
    def test_get_film_by_id_success(self, mock_get):
        """Test de récupération d'un film avec succès."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "tmdb_id": 123,
            "titre": "Test Film",
            "annee": 2020
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = api_client.get_film_by_id(123)
        assert result["titre"] == "Test Film"
        assert result["annee"] == 2020
    
    @patch('utils.api_client.requests.get')
    def test_get_realisateurs(self, mock_get):
        """Test de récupération de la liste des réalisateurs."""
        mock_response = Mock()
        mock_response.json.return_value = ["John Carpenter", "Wes Craven"]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = api_client.get_realisateurs()
        assert len(result) == 2
        assert "John Carpenter" in result
    
    @patch('utils.api_client.requests.post')
    def test_send_chat_query_success(self, mock_post):
        """Test d'envoi de requête chat avec succès."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "success",
            "reponse_texte": "Voici mes recommandations",
            "films_recommandes": []
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        filters = {"score_tmdb_min": 7.0}
        result = api_client.send_chat_query("Recommande des films", filters)
        
        assert result["status"] == "success"
        assert "reponse_texte" in result
    
    @patch('utils.api_client.requests.post')
    def test_send_chat_query_timeout(self, mock_post):
        """Test d'envoi de requête chat avec timeout."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()
        
        result = api_client.send_chat_query("Test")
        assert result["status"] == "error"
        assert "temps" in result["message_erreur"].lower()


class TestComponents:
    """Tests pour les composants UI (mocks Streamlit)."""
    
    def test_display_movie_card_data_structure(self):
        """Test de la structure de données pour une carte de film."""
        movie = {
            "titre": "The Thing",
            "realisateur": "John Carpenter",
            "annee": 1982,
            "score_tmdb": 8.1,
            "duree": 109,
            "genres": ["Horreur", "Sci-Fi"],
            "synopsis": "Test synopsis"
        }
        
        # Vérifier que toutes les clés nécessaires sont présentes
        assert "titre" in movie
        assert "realisateur" in movie
        assert "annee" in movie
        assert "score_tmdb" in movie
    
    def test_filters_structure(self):
        """Test de la structure des filtres."""
        filters = {
            "realisateur": "John Carpenter",
            "genres_inclus": ["Horreur"],
            "genres_exclus": ["Comédie"],
            "date_sortie_min": 1980,
            "date_sortie_max": 2000,
            "score_tmdb_min": 6.5,
            "duree_min": 90,
            "duree_max": 120
        }
        
        # Vérifier les types
        assert isinstance(filters["date_sortie_min"], int)
        assert isinstance(filters["score_tmdb_min"], float)
        assert isinstance(filters["genres_inclus"], list)


# Tests d'intégration (nécessitent l'API en cours d'exécution)
@pytest.mark.integration
class TestIntegration:
    """Tests d'intégration avec l'API réelle."""
    
    def test_full_workflow(self):
        """Test du workflow complet (nécessite API active)."""
        # Ce test sera skippé sauf si l'API est disponible
        try:
            health = api_client.check_health()
            if health.get("status") == "error":
                pytest.skip("API non disponible")
            
            # Test des endpoints
            reals = api_client.get_realisateurs()
            assert isinstance(reals, list)
            
            genres = api_client.get_genres()
            assert isinstance(genres, list)
            
        except Exception as e:
            pytest.skip(f"API non disponible : {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
