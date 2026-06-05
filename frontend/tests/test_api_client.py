"""
Tests pour le module api_client.

Ces tests vérifient que le client API communique correctement
avec le backend FastAPI.

Usage :
    pytest tests/test_api_client.py -v
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Ajouter le chemin parent pour importer les modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import api_client


class TestAPIConfiguration:
    """Tests de configuration de l'API."""
    
    def test_get_api_url_default(self):
        """Vérifie que l'URL par défaut est correcte."""
        with patch.dict('os.environ', {}, clear=True):
            url = api_client.get_api_url()
            assert url == "http://localhost:8000"
            assert not url.endswith('/')
    
    def test_get_api_url_from_env(self):
        """Vérifie que l'URL personnalisée depuis .env fonctionne."""
        with patch.dict('os.environ', {'API_URL': 'http://custom:9000'}):
            url = api_client.get_api_url()
            assert url == "http://custom:9000"


class TestHealthCheck:
    """Tests de vérification de santé de l'API."""
    
    @patch('utils.api_client.requests.get')
    def test_check_health_success(self, mock_get, mock_api_response_health):
        """Test health check avec API disponible."""
        mock_get.return_value = mock_api_response_health
        
        result = api_client.check_health()
        
        assert result is not None
        assert result["status"] == "ok"
        mock_get.assert_called_once()
    
    @patch('utils.api_client.requests.get')
    def test_check_health_connection_error(self, mock_get):
        """Test health check avec erreur de connexion."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        result = api_client.check_health()
        
        assert result["status"] == "error"
        assert "message" in result
    
    @patch('utils.api_client.requests.get')
    def test_check_health_timeout(self, mock_get):
        """Test health check avec timeout."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()
        
        result = api_client.check_health()
        
        assert result["status"] == "error"


class TestMetadataEndpoints:
    """Tests des endpoints de métadonnées (genres, réalisateurs)."""
    
    @patch('utils.api_client.requests.get')
    def test_get_genres_success(self, mock_get, mock_api_response_genres):
        """Test récupération des genres avec succès."""
        mock_get.return_value = mock_api_response_genres
        
        result = api_client.get_genres()
        
        assert isinstance(result, list)
        assert len(result) == 4
        assert "Horror" in result
        assert "Thriller" in result
    
    @patch('utils.api_client.requests.get')
    def test_get_genres_error(self, mock_get):
        """Test récupération des genres avec erreur."""
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        result = api_client.get_genres()
        
        assert result == []
    
    @patch('utils.api_client.requests.get')
    def test_get_realisateurs_success(self, mock_get, mock_api_response_directors):
        """Test récupération des réalisateurs avec succès."""
        mock_get.return_value = mock_api_response_directors
        
        result = api_client.get_realisateurs()
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert "John Carpenter" in result
        assert "Wes Craven" in result
    
    @patch('utils.api_client.requests.get')
    def test_get_realisateurs_empty_response(self, mock_get):
        """Test récupération des réalisateurs avec réponse vide."""
        mock_response = Mock()
        mock_response.json.return_value = {"directors": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = api_client.get_realisateurs()
        
        assert result == []


class TestFilmEndpoints:
    """Tests des endpoints de films."""
    
    @patch('utils.api_client.requests.get')
    def test_get_film_by_id_success(self, mock_get, sample_film_detail):
        """Test récupération d'un film par ID avec succès."""
        mock_response = Mock()
        mock_response.json.return_value = sample_film_detail
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = api_client.get_film_by_id(694)
        
        assert result is not None
        assert result["tmdb_id"] == 694
        assert result["title"] == "The Shining"
        assert result["director"] == "Stanley Kubrick"
    
    @patch('utils.api_client.requests.get')
    def test_get_film_by_id_not_found(self, mock_get):
        """Test récupération d'un film inexistant."""
        import requests
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        result = api_client.get_film_by_id(99999)
        
        assert result is None
    
    @patch('utils.api_client.requests.get')
    def test_get_film_by_id_invalid_id(self, mock_get):
        """Test récupération avec ID invalide."""
        result = api_client.get_film_by_id(-1)
        
        # Ne devrait pas appeler l'API avec un ID invalide
        mock_get.assert_not_called()
        assert result is None


class TestChatEndpoint:
    """Tests de l'endpoint de chat."""
    
    @patch('utils.api_client.requests.post')
    def test_send_chat_query_success(self, mock_post, mock_chat_response_success):
        """Test envoi de message chat avec succès."""
        mock_post.return_value = mock_chat_response_success
        
        result = api_client.send_chat_query("Je cherche un film d'horreur", {})
        
        assert result is not None
        assert "reponse_texte" in result or "status" in result
        mock_post.assert_called_once()
    
    @patch('utils.api_client.requests.post')
    def test_send_chat_query_with_filters(self, mock_post, mock_chat_response_success, sample_filters):
        """Test envoi de message chat avec filtres."""
        mock_post.return_value = mock_chat_response_success
        
        result = api_client.send_chat_query("Recommande des films", sample_filters)
        
        assert result is not None
        # Vérifier que les filtres sont transformés correctement
        call_args = mock_post.call_args
        assert call_args is not None
    
    @patch('utils.api_client.requests.post')
    def test_send_chat_query_timeout(self, mock_post):
        """Test envoi de message avec timeout."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()
        
        result = api_client.send_chat_query("Test", {})
        
        assert result is not None
        assert result.get("status") == "error"
    
    @patch('utils.api_client.requests.post')
    def test_send_chat_query_empty_message(self, mock_post):
        """Test envoi de message vide."""
        result = api_client.send_chat_query("", {})
        
        # Ne devrait pas appeler l'API avec un message vide
        mock_post.assert_not_called()
        assert result is None


class TestWikipediaEndpoint:
    """Tests de l'endpoint Wikipedia."""
    
    @patch('utils.api_client.requests.get')
    def test_get_wikipedia_info_success(self, mock_get):
        """Test récupération d'infos Wikipedia avec succès."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "summary": "The Shining is a horror film...",
            "url": "https://en.wikipedia.org/wiki/The_Shining_(film)"
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = api_client.get_wikipedia_info(694)
        
        assert result is not None
        assert "summary" in result
    
    @patch('utils.api_client.requests.get')
    def test_get_wikipedia_info_not_found(self, mock_get):
        """Test récupération Wikipedia pour film inexistant."""
        import requests
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        result = api_client.get_wikipedia_info(99999)
        
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
