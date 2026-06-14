# tests/test_health.py
from unittest.mock import MagicMock
from api.main import app
from database.connection import get_db

def test_health(client):

    response = client.get("/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "ok"
    }


def test_health_exception(client):
    mock_db = MagicMock()
    mock_db.execute.side_effect = Exception("DB down")

    # override dependency
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/health")

    assert response.status_code == 500
    assert "Health check failed" in response.json()["detail"]

    app.dependency_overrides.clear()