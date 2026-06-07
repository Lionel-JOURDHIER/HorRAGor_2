import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# 1. On trouve le dossier de ce conftest (database/tests)
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. On remonte au dossier 'database'
DATABASE_DIR = os.path.dirname(TESTS_DIR)

# 3. On remonte à la racine réelle du projet (HorRAGor_2)
ROOT_DIR = os.path.dirname(DATABASE_DIR)

# On injecte la racine tout en haut du path pour que 'database' et 'api' soient visibles
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

root_dir = Path(__file__).resolve().parents[2]
env_path = root_dir / ".env"

if env_path.exists():
    # override=True permet de s'assurer que les vraies valeurs écrasent les valeurs par défaut
    load_dotenv(dotenv_path=env_path, override=True)
