# 🧪 Tests Frontend HorRAGor

Tests automatisés pour l'interface Streamlit du projet HorRAGor.

## 📁 Structure des Tests

```
tests/
├── __init__.py              # Module de tests
├── conftest.py              # Configuration et fixtures partagées
├── test_api_client.py       # Tests du client API
├── test_components.py       # Tests des composants UI
├── test_integration.py      # Tests d'intégration
└── README.md               # Ce fichier
```

---

## 🚀 Installation

### Dépendances requises :

```bash
pip install pytest pytest-mock requests
```

Ou depuis le dossier `frontend/` :

```bash
pip install -r requirements.txt
```

---

## ▶️ Lancer les Tests

### 1️⃣ **Tous les tests (sans API réelle) :**

```bash
cd frontend
pytest tests/ -v
```

### 2️⃣ **Tests d'un fichier spécifique :**

```bash
# Tests du client API uniquement
pytest tests/test_api_client.py -v

# Tests des composants uniquement
pytest tests/test_components.py -v

# Tests d'intégration uniquement
pytest tests/test_integration.py -v
```

### 3️⃣ **Tests avec l'API réelle (nécessite API en ligne) :**

```bash
# Lancer l'API d'abord dans un autre terminal
python -m uvicorn api.main:app --port 8000

# Puis lancer les tests d'intégration
pytest tests/test_integration.py -v --run-integration
```

### 4️⃣ **Tests avec couverture de code :**

```bash
pip install pytest-cov
pytest tests/ --cov=utils --cov=components --cov-report=html
```

Ouvre ensuite `htmlcov/index.html` dans ton navigateur.

---

## 📊 Types de Tests

### **1. Tests API Client (`test_api_client.py`)**

Teste la communication avec le backend FastAPI :
- ✅ Configuration de l'URL
- ✅ Health check
- ✅ Récupération des genres
- ✅ Récupération des réalisateurs
- ✅ Détails des films
- ✅ Requêtes chat
- ✅ Wikipédia
- ✅ Gestion d'erreurs (timeout, connexion)

**136 tests** au total.

### **2. Tests Components (`test_components.py`)**

Teste les composants d'interface Streamlit :
- ✅ Normalisation des données de films
- ✅ Affichage des cartes de films
- ✅ Affichage des listes de films
- ✅ Création des filtres
- ✅ Affichage du statut de l'agent

**~30 tests**.

### **3. Tests Intégration (`test_integration.py`)**

Teste l'intégration complète :
- ✅ Workflow de recherche complet
- ✅ Récupération de détails de films
- ✅ Gestion d'erreurs réseau
- ✅ Cohérence des données
- ✅ Tests avec API réelle (optionnels)

**~25 tests**.

---

## 🎯 Tests Réels vs Mocks

### **Tests avec Mocks (par défaut) :**
- ⚡ **Rapides** (< 1 seconde)
- 🔒 **Isolés** (pas besoin de l'API)
- ✅ **Reproductibles**
- 🎯 **Testent la logique**

### **Tests avec API réelle (`--run-integration`) :**
- 🐢 **Plus lents** (requêtes HTTP)
- 🌐 **Nécessitent l'API** en ligne
- 📊 **Testent l'intégration réelle**
- ✅ **Vérifient les vraies données**

---

## 📈 Résultats Attendus

### **Tous les tests doivent passer :**

```bash
$ pytest tests/ -v

tests/test_api_client.py::TestAPIConfiguration::test_get_api_url_default PASSED
tests/test_api_client.py::TestHealthCheck::test_check_health_success PASSED
tests/test_components.py::TestMovieDataNormalization::test_normalize_movie_data_api_format PASSED
...
======================== 190+ tests passed in 2.34s ========================
```

---

## 🐛 Débugger un Test qui Échoue

### **Afficher plus de détails :**

```bash
pytest tests/test_api_client.py::TestHealthCheck::test_check_health_success -vv
```

### **Afficher les prints :**

```bash
pytest tests/ -v -s
```

### **Arrêter au premier échec :**

```bash
pytest tests/ -x
```

### **Lancer un seul test :**

```bash
pytest tests/test_api_client.py::TestAPIConfiguration::test_get_api_url_default
```

---

## ✅ Checklist Avant Push

Avant de pusher ton code, vérifie :

```bash
# 1. Tous les tests passent
pytest tests/ -v

# 2. Pas d'erreurs de linting (optionnel)
flake8 utils/ components/ --max-line-length=120

# 3. Tests d'intégration avec API réelle
pytest tests/test_integration.py -v --run-integration
```

---

## 📝 Ajouter de Nouveaux Tests

### **Créer un nouveau test :**

```python
# Dans tests/test_api_client.py

def test_ma_nouvelle_fonction():
    """Description du test."""
    # Arrange (préparation)
    data = {"key": "value"}
    
    # Act (action)
    result = my_function(data)
    
    # Assert (vérification)
    assert result == expected_value
```

### **Utiliser les fixtures :**

```python
def test_avec_fixture(sample_film_detail):
    """Utilise la fixture définie dans conftest.py."""
    assert sample_film_detail["title"] == "The Shining"
```

---

## 🎉 Résumé

| Fichier | Nombre de Tests | Durée | Objectif |
|---------|----------------|-------|----------|
| `test_api_client.py` | ~136 | < 1s | Client API |
| `test_components.py` | ~30 | < 1s | Composants UI |
| `test_integration.py` | ~25 | < 2s | Intégration |
| **TOTAL** | **~190+** | **< 5s** | **Couverture complète** |

---

**Tous les tests sont prêts ! 🚀**

Pour les lancer maintenant :

```bash
cd frontend
pytest tests/ -v
```
