# HorRAGor - Interface Frontend Streamlit

Interface utilisateur pour le chatbot HorRAGor, spécialisé dans les recommandations de films d'horreur.

## 📋 Description

Cette interface Streamlit permet aux utilisateurs d'interagir avec l'agent conversationnel HorRAGor via une interface de chat intuitive. L'agent utilise une architecture ReAct (Reason + Act) pour analyser les requêtes et recommander des films d'horreur personnalisés.

## 🎯 Fonctionnalités (Epic 7)

### Interface de Chat
- ✅ Chatbot classique avec saisie de texte et historique de conversation
- ✅ Affichage du statut de réflexion de l'agent en temps réel
- ✅ Indicateur de chargement pendant le traitement
- ✅ Bulles de conversation stylisées avec thème d'horreur

### Filtres de Recherche SQL
- ✅ Sélecteur de réalisateur (alimenté par `/list_real`)
- ✅ Double sélecteur de genres (inclus/exclus) via `/list_genre`
- ✅ Slider de dates de sortie (1900-2026)
- ✅ Slider de score TMDB minimum (0-10)
- ✅ Slider de durée du film (1-685 minutes)

### Affichage des Résultats
- ✅ Cartes visuelles des films avec affiches
- ✅ Informations détaillées (réalisateur, année, score, durée, genres)
- ✅ Synopsis dans un expander
- ✅ Liste des 5 films recommandés
- ✅ Détails de réflexion de l'agent (optionnel)

### Architecture
- ✅ Découplage strict de la logique métier
- ✅ Communication HTTP asynchrone avec l'API FastAPI
- ✅ Thème sombre personnalisé (.streamlit/config.toml)

## 🚀 Installation

### Prérequis
- Python >= 3.11
- API FastAPI HorRAGor en cours d'exécution

### Étapes d'installation

1. **Se placer dans le dossier frontend**
   ```bash
   cd frontend
   ```

2. **Installer les dépendances**
   ```bash
   pip install -e .
   ```
   
   Ou avec uv :
   ```bash
   uv pip install -e .
   ```

3. **Configurer les variables d'environnement**
   ```bash
   cp .env.example .env
   ```
   
   Éditer `.env` et configurer l'URL de l'API :
   ```
   API_URL=http://localhost:8000
   ```

4. **Lancer l'application**
   ```bash
   streamlit run app.py
   ```
   
   L'application sera accessible sur : http://localhost:8501

## 📁 Structure du Projet

```
frontend/
├── .streamlit/
│   └── config.toml          # Configuration du thème Streamlit
├── components/
│   ├── __init__.py
│   └── components.py        # Composants UI réutilisables
├── utils/
│   ├── __init__.py
│   └── api_client.py        # Module de communication avec l'API
├── app.py                   # Point d'entrée principal
├── pyproject.toml           # Configuration du projet et dépendances
├── .env.example             # Exemple de variables d'environnement
└── README.md                # Ce fichier
```

## 🎨 Thème Personnalisé

Le fichier `.streamlit/config.toml` configure un thème sombre "horreur" :
- **Couleur primaire** : Rouge sang (#8b0000)
- **Arrière-plan** : Noir profond (#111111)
- **Arrière-plan secondaire** : Gris sombre (#1b1f24)
- **Texte** : Gris clair (#e2e8f0)

## 🔌 Communication avec l'API

L'interface communique avec l'API FastAPI via les endpoints suivants :

- `GET /health` : Vérification de la santé de l'API
- `GET /list_real` : Liste des réalisateurs
- `GET /list_genre` : Liste des genres
- `POST /chat` : Envoi de la requête utilisateur avec filtres
- `GET /film/{id}` : Détails d'un film spécifique
- `GET /wikipedia` : Informations Wikipedia (optionnel)

## 💡 Exemples d'utilisation

### Questions types
- "Recommande-moi des films d'horreur psychologique des années 80"
- "Quels sont les meilleurs films de John Carpenter ?"
- "Je cherche des films similaires à The Shining"
- "Montre-moi des films d'horreur japonais bien notés"

### Utilisation des filtres
1. Sélectionnez un réalisateur dans la sidebar
2. Choisissez les genres souhaités/non souhaités
3. Ajustez la plage de dates de sortie
4. Définissez un score TMDB minimum
5. Réglez la durée minimale/maximale
6. Posez votre question dans le chat

## 🧪 Tests

Pour tester l'interface sans l'API backend :
```bash
# TODO: Ajouter des tests unitaires avec pytest
```

## 📝 Notes de Développement

- **Découplage** : Aucune logique métier dans l'interface, tout passe par l'API
- **Session State** : Utilisation de `st.session_state` pour l'historique de conversation
- **Gestion d'erreurs** : Messages d'erreur clairs en cas de problème API
- **Performance** : Timeout configuré à 60s pour les requêtes longues

## 🔧 Configuration Avancée

### Variables d'environnement disponibles
- `API_URL` : URL de l'API FastAPI (défaut: http://localhost:8000)

### Personnalisation du thème
Modifiez `.streamlit/config.toml` pour ajuster les couleurs.

## 📚 Dépendances

- `streamlit>=1.30.0` : Framework d'interface web
- `requests>=2.31.0` : Communication HTTP avec l'API
- `python-dotenv>=1.0.0` : Gestion des variables d'environnement
- `pillow>=10.0.0` : Manipulation d'images pour les affiches

## 👥 Auteur

**Flavie** - Epic 7 : Interface Streamlit

## 🔗 Liens Utiles

- [Documentation Streamlit](https://docs.streamlit.io/)
- [API FastAPI (Epic 6)](../api/README.md)
- [Agent LangGraph (Epic 4)](../agents/README.md)

## 📌 TODO / Améliorations Futures

- [ ] Bouton d'arrêt de la demande en cours
- [ ] Sélection de films similaires depuis les résultats
- [ ] Gestion de l'historique de conversation persistant
- [ ] Mode streaming pour voir la réflexion de l'agent en direct
- [ ] Export des recommandations en PDF
- [ ] Système de favoris/likes pour les films
