# 🚀 Guide de Démarrage Rapide - Frontend HorRAGor

## Pour Flavie et l'équipe Frontend

Ce guide vous permet de démarrer rapidement avec l'interface Streamlit.

---

## ⚡ Installation Express

```bash
# 1. Se placer dans le dossier frontend
cd frontend

# 2. Créer le fichier .env
cp .env.example .env

# 3. Installer les dépendances (au choix)
pip install -r requirements.txt
# OU
pip install -e .

# 4. Lancer l'application
streamlit run app.py
```

**L'application sera disponible sur : http://localhost:8501**

---

## ✅ Checklist Avant de Commencer

- [ ] Python 3.11+ installé
- [ ] L'API FastAPI est lancée sur http://localhost:8000
- [ ] Le fichier `.env` est configuré
- [ ] Les dépendances sont installées

---

## 🎯 Test Rapide de Connexion

Ouvrir une console Python et tester :

```python
import requests

# Test de l'API
response = requests.get("http://localhost:8000/health")
print(response.json())  # Doit retourner {"status": "ok"} ou similaire
```

Si ça ne fonctionne pas, démarrer l'API backend d'abord !

---

## 📂 Structure des Fichiers que Tu As Créés

```
frontend/
├── .streamlit/
│   └── config.toml          # ✅ Thème sombre configuré
├── components/
│   └── components.py        # ✅ Composants UI réutilisables
├── utils/
│   └── api_client.py        # ✅ Communication avec l'API
├── app.py                   # ✅ Interface principale
├── start.py                 # 🆕 Script de démarrage avec vérification
├── pyproject.toml           # ✅ Configuration du projet
├── requirements.txt         # ✅ Dépendances (alternative)
├── .env.example             # ✅ Template de configuration
├── .gitignore               # ✅ Fichiers à ignorer
└── README.md                # ✅ Documentation complète
```

---

## 🔧 Démarrage avec Script

Pour un démarrage plus contrôlé :

```bash
# Démarrage simple
python start.py

# Avec vérification de l'API
python start.py --check-api

# Sur un port différent
python start.py --port 8502
```

---

## 🎨 Fonctionnalités Implémentées (Epic 7)

### ✅ Complété
- [x] Interface de chat avec historique
- [x] Composants de chat dédiés (st.chat_input, st.chat_message)
- [x] Indicateur de chargement
- [x] Formulaire de filtres SQL dans la sidebar :
  - [x] Sélecteur de réalisateur
  - [x] Double sélecteur de genres (inclus/exclus)
  - [x] Slider dates de sortie (1900-2026)
  - [x] Slider score TMDB (0-10)
  - [x] Slider durée (1-685 min)
- [x] Affichage des réponses de l'agent
- [x] Cartes visuelles des films avec affiches
- [x] Affichage des détails des films
- [x] Liste des films recommandés
- [x] Thème sombre personnalisé
- [x] Découplage strict (pas de logique métier)

### 🔜 À Implémenter Plus Tard (Si Temps)
- [ ] Bouton d'arrêt de la demande
- [ ] Sélection de films similaires
- [ ] Historique de conversation persistant
- [ ] Mode streaming en temps réel

---

## 🐛 Dépannage

### L'application ne démarre pas
```bash
# Vérifier que Streamlit est installé
streamlit --version

# Réinstaller si nécessaire
pip install --upgrade streamlit
```

### Erreur "API non accessible"
1. Vérifier que l'API tourne : `curl http://localhost:8000/health`
2. Vérifier le `.env` : l'URL de l'API est-elle correcte ?
3. Relancer l'API backend

### Les filtres ne se chargent pas
- L'API doit avoir les endpoints `/list_real` et `/list_genre` fonctionnels
- Vérifier les logs de l'API backend

### Les affiches ne s'affichent pas
- Normal si l'API ne retourne pas de `poster_url`
- Vérifier le modèle Pydantic de l'API

---

## 📝 Notes de Développement

### Modifier les Couleurs du Thème
Éditer `.streamlit/config.toml` :
```toml
[theme]
primaryColor = "#8b0000"      # Rouge sang
backgroundColor = "#111111"    # Noir profond
```

### Ajoutercomponents/components.py`
2. Créer une nouvelle fonction
3. Importer dans `app.py`
4. Utiliser dans l'interface

### Modifier les Filtres
Tout est dans la fonction `create_filters_sidebar()` dans `component
Tout est dans la fonction `create_filters_sidebar()` dans `pages/components.py`

---

## 🤝 Coordination avec le Backend (Hanna)

### Contrat d'API Attendu

**POST /chat**
```json
{
  "prompt": "Recommande des films...",
  "filters": {
    "realisateur": "John Carpenter",
    "genres_inclus": ["Horreur", "Thriller"],
    "genres_exclus": ["Comédie"],
    "date_sortie_min": 1980,
    "date_sortie_max": 2000,
    "score_tmdb_min": 6.5,
    "duree_min": 90,
    "duree_max": 120
  }
}
```

**Réponse Attendue**
```json
{
  "status": "success",
  "reponse_texte": "Voici mes recommandations...",
  "films_recommandes": [
    {
      "tmdb_id": 123,
      "titre": "The Thing",
      "realisateur": "John Carpenter",
      "annee": 1982,
      "score_tmdb": 8.1,
      "duree": 109,
      "genres": ["Horreur", "Sci-Fi"],
      "synopsis": "...",
      "poster_url": "https://..."
    }
  ],
  "etats_agent": [...]
}
```

---

## 🎬 Prêt à Tester !

1. Lance l'API backend (demande à Hanna ou Lionel)
2. Lance le frontend : `streamlit run app.py`
3. Ouvre http://localhost:8501
4. Profite du thème d'horreur ! 🎃

---

**Bon développement ! 🚀**

*Si tu as des questions, consulte le README.md complet ou demande à l'équipe.*
