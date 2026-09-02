# api/tests/conftest.py
import os
import sys

import pytest
from fastapi.testclient import TestClient


# Dossier contenant ce conftest : api/tests
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Dossier api
API_DIR = os.path.dirname(TESTS_DIR)

# Racine du projet : HorRAGor_2
ROOT_DIR = os.path.dirname(API_DIR)

# Ajoute la racine du projet au PYTHONPATH
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from api.main import app


@pytest.fixture
def client():
    return TestClient(app)
