"""
Table des refresh tokens pour le système d'authentification JWT.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from database.tables.base import Base


class RefreshToken(Base):
    """
    Table des refresh tokens pour la gestion de sessions longues.
    
    Colonnes :
        - id : Clé primaire auto-incrémentée
        - token : Refresh token unique (UUID)
        - user_id : Clé étrangère vers la table users
        - expires_at : Date d'expiration du refresh token
        - is_revoked : Token révoqué (déconnexion)
        - created_at : Date de création du token
    """

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(500), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, revoked={self.is_revoked})>"
