"""
Configuration globale pour les tests du module database.

Ce fichier est automatiquement détecté par pytest. Il centralise l'ajustement
du path Python pour s'assurer que tous les fichiers de test du sous-dossier
peuvent importer 'connection', 'models' ou 'faiss_service' sans duplication de code.
"""

import os
import sys

# On détermine le chemin absolu du dossier parent ('database')
DATABASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# On l'ajoute au path unique de l'exécution
if DATABASE_DIR not in sys.path:
    sys.path.insert(0, DATABASE_DIR)
