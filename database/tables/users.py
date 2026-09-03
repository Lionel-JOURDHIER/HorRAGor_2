"""
Table des utilisateurs pour le système d'authentification HorRAGor.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from database.tables.base import Base


class User(Base):
    """
    Table des utilisateurs avec système d'authentification JWT.
    
    Colonnes :
        - id : Clé primaire auto-incrémentée
        - email : Adresse email unique (identifiant de connexion)
        - username : Nom d'utilisateur unique
        - hashed_password : Mot de passe hashé avec bcrypt
        - is_active : Compte actif ou désactivé
        - is_verified : Email vérifié ou non
        - created_at : Date de création du compte
        - updated_at : Date de dernière modification
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Statuts
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', username='{self.username}')>"
