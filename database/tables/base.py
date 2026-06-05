"""
data_tools/0_shared/tables/base.py
──────────────
Base déclarative partagée par tous les modèles SQLAlchemy.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy declarative models.

    This class serves as the central registry for the application's database
    schema. All models inheriting from this class will share the same
    MetaData object, enabling automated schema creation and migrations.

    Attributes:
        metadata (MetaData): The registry of all tables and schemas
                             associated with the subclasses.
    """

    pass
