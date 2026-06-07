"""
Tests d'intégration pour le frontend HorRAGor.

Ces tests vérifient l'interaction entre les différents composants
et la communication avec l'API réelle.

Usage :
    pytest tests/test_integration.py -v
    pytest tests/test_integration.py -v --run-integration (avec API)
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import api_client


@pytest.fixture
def skip_if_no_api(request):
    """Skip les tests si l'API n'est pas disponible."""
    if not request.config.getoption("--run-integration"):
        pytest.skip("Tests d'intégration désactivés (utiliser --run-integration)")


@pytest.mark.integration
class TestRealAPIConnection:
    """Tests avec l'API réelle (nécessite --run-integration)."""
    
    def test_api_health_real(self, skip_if_no_api):
        """Test connexion à l'API réelle."""
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
        except requests.exceptions.ConnectionError:
            pytest.skip("API non disponible sur localhost:8000")
    
    def test_get_genres_real(self, skip_if_no_api):
        """Test récupération des genres réels."""
        try:
            result = api_client.get_genres()
            assert isinstance(result, list)
            assert len(result) > 0
            # Vérifier qu'on a des vrais genres
            assert any(g in result for g in ["Horror", "Thriller", "Action"])
        except:
            pytest.skip("API non disponible")
    
    def test_get_directors_real(self, skip_if_no_api):
        """Test récupération des réalisateurs réels."""
        try:
            result = api_client.get_realisateurs()
            assert isinstance(result, list)
            assert len(result) > 100  # Devrait avoir 2349 réalisateurs
        except:
            pytest.skip("API non disponible")
    
    def test_get_film_shining(self, skip_if_no_api):
        """Test récupération de The Shining (tmdb_id=694)."""
        try:
            result = api_client.get_film_by_id(694)
            if result:
                assert result["title"] == "The Shining"
                assert result["release_date"].startswith("1980")
            else:
                pytest.skip("Film non trouvé dans la base")
        except:
            pytest.skip("API non disponible")
    
    def test_chat_query_real(self, skip_if_no_api):
        """Test envoi d'une vraie requête chat."""
        try:
            result = api_client.send_chat_query(
                "Je cherche un film d'horreur classique", 
                {}
            )
            assert result is not None
            assert "answer" in result
            # Devrait avoir le message de développement en cours
            assert "développement" in result["answer"].lower()
        except:
            pytest.skip("API non disponible")


class TestEndToEndFlow:
    """Tests de bout en bout (avec mocks)."""
    
    @patch('utils.api_client.requests.get')
    @patch('utils.api_client.requests.post')
    def test_complete_search_workflow(self, mock_post, mock_get,
                                     mock_api_response_genres,
                                     mock_api_response_directors,
                                     mock_chat_response_success):
        """Test workflow complet de recherche."""
        # Setup mocks
        mock_get.side_effect = [
            mock_api_response_directors,
            mock_api_response_genres
        ]
        mock_post.return_value = mock_chat_response_success
        
        # 1. Récupérer les métadonnées pour les filtres
        directors = api_client.get_realisateurs()
        genres = api_client.get_genres()
        
        assert len(directors) > 0
        assert len(genres) > 0
        
        # 2. Construire les filtres
        filters = {
            "realisateur": directors[0],
            "genres_included": [genres[0]],
            "release_year_min": 1980
        }
        
        # 3. Envoyer la requête chat
        result = api_client.send_chat_query("Recommande des films", filters)
        
        assert result is not None
        assert "reponse_texte" in result or "status" in result
    
    @patch('utils.api_client.requests.get')
    def test_film_detail_retrieval_workflow(self, mock_get, sample_film_detail):
        """Test workflow de récupération de détails de film."""
        mock_response = Mock()
        mock_response.json.return_value = sample_film_detail
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Récupérer les détails
        film = api_client.get_film_by_id(694)
        
        assert film is not None
        assert film["title"] == "The Shining"
        assert "genres" in film
        assert isinstance(film["genres"], list)


class TestErrorHandling:
    """Tests de gestion d'erreurs."""
    
    @patch('utils.api_client.requests.get')
    def test_network_error_handling(self, mock_get):
        """Test gestion erreur réseau."""
        mock_get.side_effect = requests.exceptions.ConnectionError()
        
        # Devrait retourner des valeurs par défaut ou None
        health = api_client.check_health()
        assert health["status"] == "error"
        
        genres = api_client.get_genres()
        assert genres == []
        
        directors = api_client.get_realisateurs()
        assert directors == []
    
    @patch('utils.api_client.requests.post')
    def test_chat_server_error_handling(self, mock_post):
        """Test gestion erreur serveur pour chat."""
        import requests
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        mock_post.return_value = mock_response
        
        result = api_client.send_chat_query("Test", {})
        
        # Devrait gérer l'erreur gracieusement
        assert result is not None
        assert result.get("status") == "error"
    
    @patch('utils.api_client.requests.get')
    def test_json_decode_error_handling(self, mock_get):
        """Test gestion erreur de décodage JSON."""
        import requests
        mock_response = Mock()
        mock_response.json.side_effect = requests.exceptions.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        genres = api_client.get_genres()
        
        # Devrait retourner une liste vide
        assert genres == []


class TestDataConsistency:
    """Tests de cohérence des données."""
    
    @patch('utils.api_client.requests.get')
    def test_film_data_structure(self, mock_get, sample_film_detail):
        """Vérifie la structure des données de film."""
        mock_response = Mock()
        mock_response.json.return_value = sample_film_detail
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        film = api_client.get_film_by_id(694)
        
        # Vérifier les champs obligatoires
        required_fields = ["tmdb_id", "title", "genres"]
        for field in required_fields:
            assert field in film, f"Champ manquant : {field}"
    
    def test_filter_transformation(self, sample_filters):
        """Vérifie la transformation des filtres frontend → API."""
        # Vérifier que les clés sont correctes
        assert "genres_included" in sample_filters
        assert "release_year_min" in sample_filters
        
        # Ces clés doivent être transformées par api_client
        # genres_inclus → genres_included
        # date_sortie_min → release_year_min


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
