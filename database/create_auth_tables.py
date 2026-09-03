"""
Script de migration pour créer les tables d'authentification dans Supabase.

Tables créées :
    - users : Comptes utilisateurs
    - refresh_tokens : Tokens de rafraîchissement JWT

Usage :
    python -m database.create_auth_tables
"""

import sys
from pathlib import Path

# Ajouter le dossier parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import engine
from database.tables.base import Base
from database.tables.users import User
from database.tables.refresh_tokens import RefreshToken


def create_auth_tables():
    """Crée les tables users et refresh_tokens dans la base de données."""
    
    print("🔧 Création des tables d'authentification...")
    
    try:
        # Créer uniquement les tables User et RefreshToken
        User.__table__.create(engine, checkfirst=True)
        RefreshToken.__table__.create(engine, checkfirst=True)
        
        print("✅ Tables créées avec succès :")
        print("   - users")
        print("   - refresh_tokens")
        
    except Exception as e:
        print(f"❌ Erreur lors de la création des tables : {e}")
        raise


if __name__ == "__main__":
    create_auth_tables()
