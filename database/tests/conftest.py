"""
Configuration globale pour les tests du module database.

Ce fichier est automatiquement détecté par pytest. Il centralise l'ajustement
du path Python pour s'assurer que tous les fichiers de test du sous-dossier
peuvent importer 'connection', 'models' ou 'faiss_service' sans duplication de code.
"""

import os
import sys

# 1. On trouve le dossier de ce conftest (database/tests)
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. On remonte au dossier 'database'
DATABASE_DIR = os.path.dirname(TESTS_DIR)

# 3. On remonte à la racine réelle du projet (HorRAGor_2)
ROOT_DIR = os.path.dirname(DATABASE_DIR)

# On injecte la racine tout en haut du path pour que 'database' et 'api' soient visibles
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
