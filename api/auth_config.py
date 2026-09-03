"""
Module de configuration pour le système d'authentification JWT.

Variables d'environnement requises :
    - JWT_SECRET_KEY : Clé secrète pour signer les tokens JWT
    - JWT_ALGORITHM : Algorithme de chiffrement (par défaut: HS256)
    - ACCESS_TOKEN_EXPIRE_MINUTES : Durée de vie de l'access token (par défaut: 30 minutes)
    - REFRESH_TOKEN_EXPIRE_DAYS : Durée de vie du refresh token (par défaut: 7 jours)
"""

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

# Configuration JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "votre_cle_secrete_tres_longue_et_complexe_changez_moi_en_production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Durées de vie des tokens
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

ACCESS_TOKEN_EXPIRE = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
REFRESH_TOKEN_EXPIRE = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
