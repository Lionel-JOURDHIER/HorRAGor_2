Interface HorRAGor
===================

Le frontend Streamlit constitue l'interface utilisateur de HorRAGor. Il ne
porte aucune logique métier : il consomme l'API IA et l'API Database via des
clients HTTP dédiés.

Client de chat et de données
-----------------------------

.. automodule:: frontend.utils.api_client
   :members:
   :undoc-members:
   :show-inheritance:

Client d'authentification
--------------------------

.. automodule:: frontend.utils.auth_client
   :members:
   :undoc-members:
   :show-inheritance:

Chiffrement du mot de passe côté client
-----------------------------------------

.. automodule:: frontend.utils.auth_crypto_client
   :members:
   :undoc-members:
   :show-inheritance:

Composants d'authentification
-------------------------------

.. automodule:: frontend.components.auth_components
   :members:
   :undoc-members:
   :show-inheritance:

Composants d'affichage
------------------------

.. automodule:: frontend.components.components
   :members:
   :undoc-members:
   :show-inheritance:
