# 🔐 EPIC 10 : Système d'Authentification HorRAGor
## Documentation Complète

**Version** : 1.0  
**Date** : Juillet 2026  
**Auteur** : Flavie  
**Projet** : HorRAGor - Chatbot d'Horreur Intelligent  

---

# Table des matières

1. [Démarrage Rapide (5 minutes)](#démarrage-rapide)
2. [Vue d'ensemble du projet](#vue-densemble)
3. [Architecture détaillée](#architecture)
4. [Installation complète](#installation)
5. [Guide d'utilisation](#utilisation)
6. [Exemples de code](#exemples)
7. [Tests et validation](#tests)
8. [Intégration avec les EPICs futurs](#integration)
9. [Fichiers modifiés et créés](#manifest)
10. [Troubleshooting](#troubleshooting)

---

<a name="démarrage-rapide"></a>
# 1. 🚀 Démarrage Rapide (5 minutes)

## Prérequis
- Python 3.11+
- Compte Supabase configuré
- UV package manager installé

## Installation en 3 étapes

### Étape 1 : Créer les tables (30 secondes)
```bash
cd database
python create_auth_tables.py
```

**Résultat attendu** :
```
🔧 Création des tables d'authentification...
✅ Tables créées avec succès :
  - users
  - refresh_tokens
```

### Étape 2 : Installer les dépendances (1 minute)
```bash
cd ../api
uv sync
```

**Résultat attendu** :
```
Installed 90 packages in 1.00s
```

### Étape 3 : Démarrer l'application (10 secondes)
```bash
# Terminal 1 : API
cd api
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 : Frontend
cd frontend
streamlit run app.py
```

## Première connexion

1. Ouvrir http://localhost:8501
2. Cliquer sur l'onglet **"Inscription"**
3. Remplir le formulaire :
   - Email : `test@horragor.com`
   - Nom d'utilisateur : `testuser`
   - Mot de passe : `MotDePasse123!`
4. Cliquer sur **"Créer un compte"**
5. Vous êtes automatiquement connecté ! 🎉

## Démarrage automatique (Alternative)

### Méthode 1 : Script Python
```bash
python start.py
```

### Méthode 2 : Script Bash (Linux/Mac)
```bash
chmod +x start_with_auth.sh
./start_with_auth.sh
```

### Méthode 3 : Script Batch (Windows)
```cmd
start_with_auth.bat
```

## Vérification rapide

### Test de l'API
```bash
curl http://localhost:8000/health
```

**Résultat attendu** :
```json
{"status": "ok"}
```

### Test complet
```bash
python test_auth.py
```

**Résultat attendu** :
```
✅ 1. Health check : API accessible
✅ 2. Inscription réussie
✅ 3. Profil récupéré
✅ 4. Tokens rafraîchis
✅ 5. Connexion réussie
✅ 6. Déconnexion réussie

🎉 Tous les tests sont passés !
```

---

<a name="vue-densemble"></a>
# 2. 📖 Vue d'ensemble du projet

## Contexte

**HorRAGor** est un chatbot conversationnel spécialisé dans les recommandations de films d'horreur. L'EPIC 10 ajoute un système d'authentification complet pour :

- ✅ Sécuriser l'accès à l'application
- ✅ Gérer les comptes utilisateurs
- ✅ Préparer la personnalisation (mémoire, historique)
- ✅ Permettre le tracking et l'analyse par utilisateur

## Objectifs EPIC 10

### Cahier des charges
```
✅ Mise en place de refresh Token
✅ Mise en place BDD utilisateur
✅ Page de connexion en Front
✅ Contrainte : La base est sur Supabase
```

**Résultat : 4/4 objectifs atteints** 🎉

## Fonctionnalités implémentées

### 🗄️ Base de données (Supabase PostgreSQL)

#### Table `users`
| Colonne | Type | Description |
|---------|------|-------------|
| id | SERIAL PRIMARY KEY | Identifiant unique |
| email | VARCHAR(255) UNIQUE | Email de l'utilisateur |
| username | VARCHAR(100) UNIQUE | Nom d'utilisateur |
| hashed_password | VARCHAR(255) | Hash bcrypt du mot de passe |
| is_active | BOOLEAN | Compte actif (par défaut TRUE) |
| is_verified | BOOLEAN | Email vérifié (par défaut FALSE) |
| created_at | TIMESTAMP | Date de création |
| updated_at | TIMESTAMP | Date de modification |

#### Table `refresh_tokens`
| Colonne | Type | Description |
|---------|------|-------------|
| id | SERIAL PRIMARY KEY | Identifiant unique |
| token | VARCHAR(500) UNIQUE | Token JWT |
| user_id | INTEGER FK | Référence vers users.id |
| expires_at | TIMESTAMP | Date d'expiration |
| is_revoked | BOOLEAN | Token révoqué (par défaut FALSE) |
| created_at | TIMESTAMP | Date de création |

### 🔐 Sécurité JWT

#### Configuration
```python
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
```

#### Flow de tokens
1. **Inscription/Connexion** → Génération access_token (30 min) + refresh_token (7 jours)
2. **Access token expiré** → Utiliser refresh_token pour obtenir de nouveaux tokens
3. **Déconnexion** → Révocation du refresh_token en base de données

#### Hash des mots de passe
- **Algorithme** : bcrypt
- **Rounds** : 12
- **Salage** : Automatique

### 🌐 Backend API (FastAPI)

#### 6 endpoints d'authentification

| Endpoint | Méthode | Description | Protection |
|----------|---------|-------------|------------|
| `/auth/register` | POST | Créer un compte | Non |
| `/auth/login` | POST | Se connecter | Non |
| `/auth/refresh` | POST | Rafraîchir les tokens | Non |
| `/auth/logout` | POST | Se déconnecter | Non |
| `/auth/logout-all` | POST | Déconnexion globale | Oui |
| `/auth/me` | GET | Profil utilisateur | Oui |

#### Middleware de protection

Tous les endpoints protégés utilisent :
```python
from api.auth_utils import get_current_user
from fastapi import Depends

@router.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"user": current_user.username}
```

### 🎨 Frontend (Streamlit)

#### Page de connexion/inscription
- Design horror cohérent (rouge sang #8B0000)
- Deux onglets : "Connexion" et "Inscription"
- Validation des formulaires
- Messages d'erreur clairs
- Redirection automatique après connexion

#### Gestion de session
Stockage dans `st.session_state` :
```python
{
    "access_token": "eyJ0eXAi...",
    "refresh_token": "eyJ0eXAi...",
    "user": {
        "id": 1,
        "email": "user@example.com",
        "username": "testuser",
        "is_active": true,
        "is_verified": false
    }
}
```

#### Protection de l'application
```python
# Avant : Application accessible à tous
def main():
    st.title("HorRAGor")
    # ... contenu de l'app

# Après : Vérification de l'authentification
def main():
    if not check_authentication():
        render_login_page()
        return
    
    logout_button()
    st.title("HorRAGor")
    # ... contenu de l'app
```

## Statistiques du projet

### Code source
- ✨ **18 nouveaux fichiers** créés
- ✏️ **6 fichiers existants** modifiés
- 💻 **~2750 lignes de code** ajoutées

### Dépendances ajoutées
- `passlib[bcrypt]>=1.7.4` - Hash de mots de passe
- `python-jose[cryptography]>=3.3.0` - JWT
- Total : **90 packages** installés

### Tables créées
- `users` - Comptes utilisateurs
- `refresh_tokens` - Gestion des sessions

---

<a name="architecture"></a>
# 3. 🏗️ Architecture détaillée

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                         HorRAGor                                │
│                   Architecture d'authentification               │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Frontend   │         │   Backend    │         │   Database   │
│  (Streamlit) │ ◄────► │  (FastAPI)   │ ◄────► │  (Supabase)  │
└──────────────┘         └──────────────┘         └──────────────┘
      │                        │                        │
      │                        │                        │
   Components              Auth Routes               Tables
      │                        │                        │
   ├─ Login Form           ├─ /register             ├─ users
   ├─ Register Form        ├─ /login                └─ refresh_tokens
   ├─ Logout Button        ├─ /refresh
   └─ Auth Check           ├─ /logout
                           ├─ /logout-all
                           └─ /me
```

## Flow d'inscription

```
┌──────────┐                                                  
│ Frontend │                                                  
└────┬─────┘                                                  
     │                                                         
     │ 1. Soumettre formulaire                                
     │    POST /auth/register                                 
     │    {email, username, password}                         
     ▼                                                         
┌──────────┐                                                  
│ Backend  │                                                  
└────┬─────┘                                                  
     │                                                         
     │ 2. Valider données (Pydantic)                         
     │    - Email format                                      
     │    - Username min 3 chars                             
     │    - Password min 8 chars                             
     ▼                                                         
     │ 3. Vérifier unicité                                    
     │    - Email existe ?                                    
     │    - Username existe ?                                 
     ▼                                                         
     │ 4. Hash password (bcrypt)                             
     │    rounds = 12                                         
     ▼                                                         
     │ 5. Créer utilisateur en DB                            
     ▼                                                         
┌──────────┐                                                  
│ Database │                                                  
└────┬─────┘                                                  
     │                                                         
     │ 6. INSERT INTO users                                   
     ▼                                                         
     │ 7. Retour user créé                                    
     │                                                         
┌────▼─────┐                                                  
│ Backend  │                                                  
└────┬─────┘                                                  
     │                                                         
     │ 8. Générer tokens JWT                                  
     │    - access_token (30 min)                            
     │    - refresh_token (7 jours)                          
     ▼                                                         
     │ 9. Stocker refresh_token                              
     ▼                                                         
┌──────────┐                                                  
│ Database │                                                  
└────┬─────┘                                                  
     │                                                         
     │ 10. INSERT INTO refresh_tokens                         
     ▼                                                         
     │ 11. Retour OK                                          
     │                                                         
┌────▼─────┐                                                  
│ Backend  │                                                  
└────┬─────┘                                                  
     │                                                         
     │ 12. Retourner réponse                                  
     │     {user, access_token, refresh_token}               
     ▼                                                         
┌──────────┐                                                  
│ Frontend │                                                  
└────┬─────┘                                                  
     │                                                         
     │ 13. Stocker dans session_state                         
     │     - access_token                                     
     │     - refresh_token                                    
     │     - user (dict)                                      
     ▼                                                         
     │ 14. Redirection vers app                               
     │                                                         
     ✅ Utilisateur connecté !                                
```

## Flow de connexion

```
┌──────────┐
│ Frontend │
└────┬─────┘
     │
     │ 1. POST /auth/login
     │    {email, password}
     ▼
┌──────────┐
│ Backend  │
└────┬─────┘
     │
     │ 2. Rechercher user par email
     ▼
┌──────────┐
│ Database │
└────┬─────┘
     │
     │ 3. SELECT * FROM users WHERE email = ?
     ▼
┌────▼─────┐
│ Backend  │
└────┬─────┘
     │
     │ 4. Vérifier password
     │    verify_password(input, hashed)
     ├─ ❌ Invalide → 401 Unauthorized
     ▼
     │ 5. Générer nouveaux tokens
     │    - access_token (30 min)
     │    - refresh_token (7 jours)
     ▼
     │ 6. Stocker refresh_token
     ▼
┌──────────┐
│ Database │
└────┬─────┘
     │
     │ 7. INSERT INTO refresh_tokens
     ▼
┌────▼─────┐
│ Backend  │
└────┬─────┘
     │
     │ 8. Retourner tokens + user
     ▼
┌──────────┐
│ Frontend │
└────┬─────┘
     │
     │ 9. Stocker dans session_state
     ▼
     ✅ Connecté !
```

## Flow de rafraîchissement

```
┌──────────┐
│ Frontend │
└────┬─────┘
     │
     │ 1. Access token expiré
     │    (détecté lors d'un appel API → 401)
     ▼
     │ 2. POST /auth/refresh
     │    {refresh_token}
     ▼
┌──────────┐
│ Backend  │
└────┬─────┘
     │
     │ 3. Valider refresh_token
     │    - Signature valide ?
     │    - Pas expiré ?
     ▼
     │ 4. Chercher en DB
     ▼
┌──────────┐
│ Database │
└────┬─────┘
     │
     │ 5. SELECT * FROM refresh_tokens WHERE token = ?
     ├─ ❌ Révoqué → 401
     ├─ ❌ Expiré → 401
     ▼
┌────▼─────┐
│ Backend  │
└────┬─────┘
     │
     │ 6. Générer NOUVEAUX tokens
     │    - access_token (30 min)
     │    - refresh_token (7 jours)
     ▼
     │ 7. RÉVOQUER ancien refresh_token
     ▼
┌──────────┐
│ Database │
└────┬─────┘
     │
     │ 8. UPDATE refresh_tokens SET is_revoked = TRUE
     │ 9. INSERT nouveau refresh_token
     ▼
┌────▼─────┐
│ Backend  │
└────┬─────┘
     │
     │ 10. Retourner nouveaux tokens
     ▼
┌──────────┐
│ Frontend │
└────┬─────┘
     │
     │ 11. Mettre à jour session_state
     ▼
     ✅ Session prolongée !
```

## Flow de déconnexion

```
┌──────────┐
│ Frontend │
└────┬─────┘
     │
     │ 1. Clic sur bouton "Déconnexion"
     ▼
     │ 2. POST /auth/logout
     │    {refresh_token}
     ▼
┌──────────┐
│ Backend  │
└────┬─────┘
     │
     │ 3. Révoquer le refresh_token
     ▼
┌──────────┐
│ Database │
└────┬─────┘
     │
     │ 4. UPDATE refresh_tokens
     │    SET is_revoked = TRUE
     │    WHERE token = ?
     ▼
┌────▼─────┐
│ Backend  │
└────┬─────┘
     │
     │ 5. Retourner succès
     ▼
┌──────────┐
│ Frontend │
└────┬─────┘
     │
     │ 6. Vider session_state
     │    - access_token = None
     │    - refresh_token = None
     │    - user = None
     ▼
     │ 7. Afficher page de connexion
     ▼
     ✅ Déconnecté !
```

## Flow de protection de route

```
┌──────────┐
│ Frontend │
└────┬─────┘
     │
     │ 1. Appel API protégé
     │    GET /auth/me
     │    Headers: {Authorization: "Bearer <token>"}
     ▼
┌──────────┐
│ Backend  │
└────┬─────┘
     │
     │ 2. Middleware get_current_user()
     │    - Extraire token du header
     ├─ ❌ Pas de header → 401
     ▼
     │ 3. Décoder access_token
     │    - Signature valide ?
     │    - Pas expiré ?
     ├─ ❌ Invalide/expiré → 401
     ▼
     │ 4. Extraire user_id du payload
     │    payload = {"sub": user_id, "email": "..."}
     ▼
     │ 5. Chercher user en DB
     ▼
┌──────────┐
│ Database │
└────┬─────┘
     │
     │ 6. SELECT * FROM users WHERE id = ?
     ├─ ❌ Pas trouvé → 401
     ├─ ❌ is_active = FALSE → 401
     ▼
┌────▼─────┐
│ Backend  │
└────┬─────┘
     │
     │ 7. Injecter user dans route
     │    current_user: User = Depends(get_current_user)
     ▼
     │ 8. Exécuter la route
     │    return {"user": current_user.username}
     ▼
┌──────────┐
│ Frontend │
└────┬─────┘
     │
     ✅ Réponse reçue !
```

## Structure des fichiers

```
HorRAGor_2/
│
├── database/
│   ├── tables/
│   │   ├── users.py                 ← Modèle User
│   │   └── refresh_tokens.py        ← Modèle RefreshToken
│   ├── models.py                    ← Import des modèles
│   └── create_auth_tables.py        ← Script de migration
│
├── api/
│   ├── auth_config.py               ← Configuration JWT
│   ├── auth_utils.py                ← Utilitaires auth (9 fonctions)
│   ├── auth_routes.py               ← 6 endpoints auth
│   ├── main.py                      ← App FastAPI (modifiée)
│   ├── schemas.py                   ← Schémas Pydantic (modifiés)
│   └── pyproject.toml               ← Dépendances (modifiées)
│
├── frontend/
│   ├── utils/
│   │   └── auth_client.py           ← Client API auth (5 fonctions)
│   ├── components/
│   │   └── auth_components.py       ← UI auth (5 composants)
│   └── app.py                       ← App Streamlit (modifiée)
│
├── test_auth.py                     ← Tests complets
├── start.py                         ← Script de démarrage Python
├── start_with_auth.sh               ← Script de démarrage Bash
├── start_with_auth.bat              ← Script de démarrage Windows
└── .env.example                     ← Variables d'environnement (modifié)
```

## Détails des modules

### database/tables/users.py
```python
class User(Base):
    """Modèle ORM pour les utilisateurs."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### api/auth_utils.py - Fonctions clés

#### 1. hash_password()
```python
def hash_password(password: str) -> str:
    """Hash un mot de passe avec bcrypt."""
    return pwd_context.hash(password)
```

#### 2. verify_password()
```python
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe contre son hash."""
    return pwd_context.verify(plain_password, hashed_password)
```

#### 3. create_access_token()
```python
def create_access_token(data: dict) -> str:
    """Crée un JWT access token (30 min)."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
```

#### 4. get_current_user() - Middleware
```python
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Middleware de protection des routes."""
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    
    # Récupérer user en DB
    db = next(get_db())
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.is_active:
        raise HTTPException(status_code=401)
    
    return user
```

---

<a name="installation"></a>
# 4. 📥 Installation complète

## Prérequis

### Logiciels requis
- **Python 3.11+**
- **UV package manager** (ou pip)
- **Git**
- **PostgreSQL** (via Supabase)

### Compte Supabase
1. Créer un compte sur https://supabase.com
2. Créer un nouveau projet
3. Noter les credentials :
   - Host
   - Database name
   - User
   - Password
   - Port

## Étape 1 : Cloner le projet

```bash
git clone https://github.com/Lionel-JOURDHIER/HorRAGor_2.git
cd HorRAGor_2
```

## Étape 2 : Configuration de l'environnement

### Créer le fichier .env

```bash
cp .env.example .env
```

### Éditer .env

```bash
# Database Supabase
SUPABASE_HOST=your-project.supabase.co
SUPABASE_DB=postgres
SUPABASE_USER=postgres
SUPABASE_PASSWORD=your-password
SUPABASE_PORT=5432

# JWT Configuration (IMPORTANT : Changer en production !)
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# API Configuration
API_HOST=localhost
API_PORT=8000
```

### Générer une clé JWT sécurisée

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Copier le résultat dans `JWT_SECRET_KEY`.

## Étape 3 : Créer les tables

```bash
cd database
python create_auth_tables.py
```

**Résultat attendu** :
```
🔧 Création des tables d'authentification...
✅ Tables créées avec succès :
  - users
  - refresh_tokens
```

**Vérification dans Supabase** :
1. Ouvrir Supabase Dashboard
2. Aller dans "Table Editor"
3. Vérifier la présence de `users` et `refresh_tokens`

## Étape 4 : Installer les dépendances

### Backend (API)

```bash
cd ../api
uv sync
```

**Packages installés** (90 au total) :
- fastapi==0.136.3
- uvicorn
- sqlalchemy==2.0.50
- psycopg2-binary
- passlib[bcrypt]==1.7.4
- python-jose[cryptography]==3.5.0
- python-multipart
- pydantic[email]
- ... et leurs dépendances

### Frontend (Streamlit)

```bash
cd ../frontend
pip install -r requirements.txt
```

**Packages installés** :
- streamlit
- requests
- ... et leurs dépendances

## Étape 5 : Vérifier l'installation

### Test 1 : Connection base de données

```bash
cd ../database
python -c "from connection import engine; print(engine.connect())"
```

**Résultat attendu** : Pas d'erreur

### Test 2 : Import des modèles

```bash
python -c "from models import User, RefreshToken; print('OK')"
```

**Résultat attendu** : `OK`

### Test 3 : Démarrer l'API

```bash
cd ../api
uv run uvicorn main:app --reload
```

Ouvrir http://localhost:8000/docs

**Résultat attendu** : Swagger UI avec les endpoints `/auth/*`

### Test 4 : Tests complets

```bash
cd ..
python test_auth.py
```

**Résultat attendu** : Tous les tests passent ✅

## Étape 6 : Premier démarrage

### Terminal 1 : API
```bash
cd api
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2 : Frontend
```bash
cd frontend
streamlit run app.py
```

### Navigateur
Ouvrir http://localhost:8501

## Troubleshooting installation

### Erreur : "ModuleNotFoundError: No module named 'passlib'"

**Solution** :
```bash
cd api
uv sync --force
```

### Erreur : "Connection refused" lors de la création des tables

**Cause** : Credentials Supabase incorrects

**Solution** :
1. Vérifier `.env`
2. Tester la connexion :
```bash
python -c "from database.connection import engine; print(engine.connect())"
```

### Erreur : "JWT_SECRET_KEY not found"

**Solution** :
1. Vérifier que `.env` existe
2. Vérifier que `JWT_SECRET_KEY` est défini
3. Redémarrer l'API

---

<a name="utilisation"></a>
# 5. 📘 Guide d'utilisation

## Inscription d'un nouvel utilisateur

### Via l'interface Streamlit

1. Ouvrir http://localhost:8501
2. Cliquer sur l'onglet **"Inscription"**
3. Remplir le formulaire :
   - **Email** : Doit être valide (format email)
   - **Nom d'utilisateur** : Min 3 caractères
   - **Mot de passe** : Min 8 caractères
4. Cliquer sur **"Créer un compte"**
5. Redirection automatique vers l'application

### Via l'API (curl)

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "MotDePasse123!"
  }'
```

**Réponse** :
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "testuser",
    "is_active": true,
    "is_verified": false,
    "created_at": "2026-07-10T12:00:00",
    "updated_at": "2026-07-10T12:00:00"
  },
  "access_token": "eyJ0eXAiOiJKV1QiLCJh...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJh...",
  "token_type": "bearer"
}
```

### Via l'API (Python)

```python
import requests

response = requests.post(
    "http://localhost:8000/auth/register",
    json={
        "email": "user@example.com",
        "username": "testuser",
        "password": "MotDePasse123!"
    }
)

data = response.json()
access_token = data["access_token"]
refresh_token = data["refresh_token"]
user = data["user"]
```

## Connexion

### Via l'interface Streamlit

1. Ouvrir http://localhost:8501
2. Onglet **"Connexion"** (par défaut)
3. Remplir :
   - **Email**
   - **Mot de passe**
4. Cliquer sur **"Se connecter"**

### Via l'API

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "MotDePasse123!"
  }'
```

## Accéder à son profil

### Via l'API

```bash
# Récupérer le token lors de la connexion
ACCESS_TOKEN="eyJ0eXAiOiJKV1QiLCJh..."

curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Réponse** :
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "testuser",
  "is_active": true,
  "is_verified": false,
  "created_at": "2026-07-10T12:00:00",
  "updated_at": "2026-07-10T12:00:00"
}
```

## Rafraîchir les tokens

### Quand rafraîchir ?

Lorsque l'access token expire (après 30 minutes), l'API retourne :
```json
{
  "detail": "Invalid or expired token"
}
```

### Via l'API

```bash
REFRESH_TOKEN="eyJ0eXAiOiJKV1QiLCJh..."

curl -X POST "http://localhost:8000/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}"
```

**Réponse** :
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJh...",  # Nouveau
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJh...", # Nouveau
  "token_type": "bearer"
}
```

⚠️ **Important** : L'ancien refresh token est révoqué automatiquement.

### Gestion automatique dans le frontend

Le frontend Streamlit gère automatiquement le rafraîchissement :

```python
# Dans utils/auth_client.py
def api_call_with_refresh(url, method="GET", **kwargs):
    """Appel API avec rafraîchissement automatique."""
    access_token = st.session_state.get("access_token")
    
    # Premier essai avec access token
    response = requests.request(
        method, url,
        headers={"Authorization": f"Bearer {access_token}"},
        **kwargs
    )
    
    # Si 401, rafraîchir et réessayer
    if response.status_code == 401:
        refresh_token = st.session_state.get("refresh_token")
        new_tokens = refresh_access_token(refresh_token)
        
        # Mettre à jour session
        st.session_state["access_token"] = new_tokens["access_token"]
        st.session_state["refresh_token"] = new_tokens["refresh_token"]
        
        # Réessayer
        response = requests.request(
            method, url,
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
            **kwargs
        )
    
    return response
```

## Déconnexion

### Via l'interface Streamlit

1. Cliquer sur le bouton **"🚪 Se déconnecter"** dans la sidebar
2. Confirmation automatique
3. Redirection vers la page de connexion

### Via l'API (déconnexion simple)

```bash
REFRESH_TOKEN="eyJ0eXAiOiJKV1QiLCJh..."

curl -X POST "http://localhost:8000/auth/logout" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}"
```

**Réponse** :
```json
{
  "message": "Successfully logged out"
}
```

### Via l'API (déconnexion de tous les appareils)

```bash
ACCESS_TOKEN="eyJ0eXAiOiJKV1QiLCJh..."

curl -X POST "http://localhost:8000/auth/logout-all" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Réponse** :
```json
{
  "message": "Successfully logged out from all devices"
}
```

## Utilisation dans l'application HorRAGor

### Avant l'authentification

```python
# frontend/app.py (avant)
def main():
    st.title("🎬 HorRAGor - Chatbot d'Horreur")
    
    # L'utilisateur pouvait utiliser l'app sans connexion
    user_input = st.text_input("Posez votre question")
    # ...
```

### Après l'authentification

```python
# frontend/app.py (après)
from components.auth_components import check_authentication, render_login_page, logout_button

def main():
    # 1. Vérifier l'authentification
    if not check_authentication():
        render_login_page()
        return  # Arrêter l'exécution
    
    # 2. Afficher bouton de déconnexion
    logout_button()
    
    # 3. L'application normale
    st.title("🎬 HorRAGor - Chatbot d'Horreur")
    user_input = st.text_input("Posez votre question")
    # ...
```

### Accéder aux informations utilisateur

```python
# Dans n'importe quelle page Streamlit
import streamlit as st

# Récupérer l'utilisateur connecté
user = st.session_state.get("user")

if user:
    st.write(f"Bienvenue {user['username']} !")
    st.write(f"Email : {user['email']}")
    st.write(f"Compte créé le : {user['created_at']}")
```

### Protéger une route API

```python
# Dans api/routes.py
from api.auth_utils import get_current_user
from fastapi import Depends

@router.get("/my-protected-route")
async def protected_route(current_user: User = Depends(get_current_user)):
    """Route protégée accessible uniquement aux utilisateurs authentifiés."""
    return {
        "message": f"Bonjour {current_user.username}",
        "user_id": current_user.id
    }
```

### Appeler une route protégée depuis le frontend

```python
# Dans frontend/utils/api_client.py
import requests
import streamlit as st

def call_protected_route():
    """Appeler une route protégée."""
    access_token = st.session_state.get("access_token")
    
    response = requests.get(
        "http://localhost:8000/my-protected-route",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Erreur d'authentification")
        return None
```

---

<a name="exemples"></a>
# 6. 💻 Exemples de code

## Exemple 1 : Créer une nouvelle route protégée

### Backend : Ajouter une route protégée

```python
# api/routes.py (ou créer api/user_routes.py)
from fastapi import APIRouter, Depends
from api.auth_utils import get_current_user
from database.models import User

router = APIRouter(prefix="/user", tags=["User"])

@router.get("/profile")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Récupère le profil complet de l'utilisateur connecté."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat(),
        "updated_at": current_user.updated_at.isoformat()
    }

@router.put("/profile")
async def update_user_profile(
    username: str,
    current_user: User = Depends(get_current_user)
):
    """Modifie le nom d'utilisateur."""
    from database.connection import get_db
    
    db = next(get_db())
    current_user.username = username
    db.commit()
    
    return {"message": "Profil mis à jour", "username": username}

@router.get("/preferences")
async def get_user_preferences(current_user: User = Depends(get_current_user)):
    """Récupère les préférences utilisateur (à implémenter avec EPIC 2)."""
    return {
        "user_id": current_user.id,
        "preferences": {
            "theme": "dark",
            "horror_level": "extreme",
            "favorite_genres": ["Gore", "Psychologique"]
        }
    }
```

### Enregistrer le nouveau router

```python
# api/main.py
from fastapi import FastAPI
from api.auth_routes import router as auth_router
from api.routes import router as main_router
from api.user_routes import router as user_router  # ← Nouveau

app = FastAPI(title="HorRAGor API")

# Enregistrer les routers
app.include_router(auth_router)
app.include_router(main_router)
app.include_router(user_router)  # ← Nouveau
```

### Frontend : Appeler la route

```python
# frontend/utils/api_client.py
def get_user_profile():
    """Récupère le profil utilisateur."""
    access_token = st.session_state.get("access_token")
    
    response = requests.get(
        f"{get_api_url()}/user/profile",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    if response.status_code == 200:
        return response.json()
    return None

def update_username(new_username: str):
    """Modifie le nom d'utilisateur."""
    access_token = st.session_state.get("access_token")
    
    response = requests.put(
        f"{get_api_url()}/user/profile",
        params={"username": new_username},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    return response.status_code == 200
```

### Frontend : Afficher dans Streamlit

```python
# frontend/pages/profile.py
import streamlit as st
from utils.api_client import get_user_profile, update_username

st.title("Mon Profil")

# Charger le profil
profile = get_user_profile()

if profile:
    st.subheader("Informations")
    st.write(f"**Email** : {profile['email']}")
    st.write(f"**Nom d'utilisateur** : {profile['username']}")
    st.write(f"**Compte créé le** : {profile['created_at']}")
    
    # Modifier le nom d'utilisateur
    st.subheader("Modifier le profil")
    new_username = st.text_input("Nouveau nom d'utilisateur", value=profile['username'])
    
    if st.button("Mettre à jour"):
        if update_username(new_username):
            st.success("Profil mis à jour !")
            st.session_state["user"]["username"] = new_username
            st.rerun()
        else:
            st.error("Erreur lors de la mise à jour")
```

## Exemple 2 : Logout personnalisé

### Backend : Ajouter des métadonnées au logout

```python
# api/auth_routes.py (modifier la route existante)
from datetime import datetime

@router.post("/logout")
async def logout(token_refresh: TokenRefresh):
    """Déconnexion avec logging."""
    from database.connection import get_db
    from database.models import RefreshToken
    
    db = next(get_db())
    
    # Trouver le token
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == token_refresh.refresh_token
    ).first()
    
    if db_token:
        # Récupérer l'user_id pour le log
        user_id = db_token.user_id
        
        # Révoquer
        db_token.is_revoked = True
        db.commit()
        
        # Logger la déconnexion
        print(f"[{datetime.utcnow()}] User {user_id} logged out")
        
        return {
            "message": "Successfully logged out",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    return {"message": "Token not found or already revoked"}
```

### Frontend : Logout avec confirmation

```python
# frontend/components/auth_components.py (modifier la fonction existante)
def logout_button():
    """Affiche le bouton de déconnexion avec confirmation."""
    user = st.session_state.get("user")
    
    if user:
        with st.sidebar:
            st.divider()
            st.write(f"👤 **{user['username']}**")
            st.caption(user['email'])
            
            # Bouton avec confirmation
            if st.button("🚪 Se déconnecter", key="logout_btn", use_container_width=True):
                # Demander confirmation
                if st.session_state.get("logout_confirm"):
                    # Déconnexion confirmée
                    refresh_token = st.session_state.get("refresh_token")
                    
                    try:
                        logout_user(refresh_token)
                        
                        # Vider la session
                        st.session_state.clear()
                        st.success("Déconnexion réussie !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")
                else:
                    # Première fois, demander confirmation
                    st.session_state["logout_confirm"] = True
                    st.warning("Cliquer à nouveau pour confirmer la déconnexion")
                    st.rerun()
```

## Exemple 3 : Intégration OAuth (GitHub/Google)

### Backend : Ajouter route OAuth

```python
# api/oauth_routes.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
import requests

router = APIRouter(prefix="/auth/oauth", tags=["OAuth"])

# Configuration OAuth (à mettre dans auth_config.py)
GITHUB_CLIENT_ID = "your-github-client-id"
GITHUB_CLIENT_SECRET = "your-github-client-secret"
GITHUB_REDIRECT_URI = "http://localhost:8000/auth/oauth/github/callback"

@router.get("/github")
async def github_login():
    """Redirige vers GitHub pour l'authentification."""
    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_REDIRECT_URI}"
        f"&scope=user:email"
    )
    return RedirectResponse(github_auth_url)

@router.get("/github/callback")
async def github_callback(code: str):
    """Callback GitHub après authentification."""
    from database.connection import get_db
    from database.models import User
    from api.auth_utils import create_access_token, create_refresh_token
    
    # Échanger le code contre un access token GitHub
    token_response = requests.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code
        },
        headers={"Accept": "application/json"}
    )
    
    access_token = token_response.json().get("access_token")
    
    # Récupérer les infos utilisateur GitHub
    user_response = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    github_user = user_response.json()
    github_email = github_user.get("email")
    github_username = github_user.get("login")
    
    # Trouver ou créer l'utilisateur
    db = next(get_db())
    user = db.query(User).filter(User.email == github_email).first()
    
    if not user:
        # Créer un nouvel utilisateur
        user = User(
            email=github_email,
            username=github_username,
            hashed_password="",  # Pas de mot de passe pour OAuth
            is_verified=True  # GitHub vérifie l'email
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Générer nos tokens JWT
    our_access_token = create_access_token({"sub": user.id, "email": user.email})
    our_refresh_token = create_refresh_token({"sub": user.id})
    
    # Rediriger vers le frontend avec les tokens
    frontend_url = f"http://localhost:8501?access_token={our_access_token}&refresh_token={our_refresh_token}"
    return RedirectResponse(frontend_url)
```

### Frontend : Bouton OAuth

```python
# frontend/components/auth_components.py (ajouter dans render_login_page)
def render_login_page():
    """Page de connexion avec OAuth."""
    st.markdown("# 🔐 Connexion à HorRAGor")
    
    tab1, tab2, tab3 = st.tabs(["Connexion", "Inscription", "OAuth"])
    
    with tab1:
        render_login_form()
    
    with tab2:
        render_register_form()
    
    with tab3:
        st.subheader("Connexion via OAuth")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🐙 GitHub", use_container_width=True):
                # Ouvrir la page OAuth GitHub
                oauth_url = "http://localhost:8000/auth/oauth/github"
                st.markdown(f"[Cliquer ici pour se connecter via GitHub]({oauth_url})")
        
        with col2:
            if st.button("🔵 Google", use_container_width=True):
                st.info("Google OAuth à implémenter")
```

## Exemple 4 : Middleware de logging

### Backend : Logger toutes les requêtes avec user_id

```python
# api/middleware.py
from fastapi import Request
from api.auth_utils import decode_access_token
import logging

logger = logging.getLogger(__name__)

async def log_requests_middleware(request: Request, call_next):
    """Middleware pour logger toutes les requêtes avec user_id."""
    
    # Extraire le token si présent
    auth_header = request.headers.get("Authorization")
    user_id = None
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
        except:
            pass
    
    # Logger la requête
    logger.info(
        f"[{request.method}] {request.url.path} "
        f"- User: {user_id or 'Anonymous'} "
        f"- IP: {request.client.host}"
    )
    
    # Exécuter la requête
    response = await call_next(request)
    
    # Logger la réponse
    logger.info(
        f"[{request.method}] {request.url.path} "
        f"- Status: {response.status_code}"
    )
    
    return response
```

### Enregistrer le middleware

```python
# api/main.py
from api.middleware import log_requests_middleware

app = FastAPI()

# Ajouter le middleware
app.middleware("http")(log_requests_middleware)
```

## Exemple 5 : Rate limiting par utilisateur

### Backend : Limiter les requêtes

```python
# api/rate_limit.py
from fastapi import HTTPException, Depends
from api.auth_utils import get_current_user
from database.models import User
from datetime import datetime, timedelta
from collections import defaultdict

# Stockage en mémoire (à remplacer par Redis en production)
request_counts = defaultdict(list)

def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """
    Rate limiter par utilisateur.
    
    Args:
        max_requests: Nombre max de requêtes
        window_seconds: Fenêtre de temps en secondes
    """
    def dependency(current_user: User = Depends(get_current_user)):
        user_id = current_user.id
        now = datetime.utcnow()
        
        # Nettoyer les anciennes requêtes
        cutoff = now - timedelta(seconds=window_seconds)
        request_counts[user_id] = [
            req_time for req_time in request_counts[user_id]
            if req_time > cutoff
        ]
        
        # Vérifier la limite
        if len(request_counts[user_id]) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {max_requests} requests per {window_seconds}s"
            )
        
        # Enregistrer cette requête
        request_counts[user_id].append(now)
        
        return current_user
    
    return dependency
```

### Utilisation

```python
# api/routes.py
from api.rate_limit import rate_limit

@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(rate_limit(max_requests=5, window_seconds=60))
):
    """Endpoint limité à 5 requêtes par minute."""
    # ... traitement normal
    pass
```

---

<a name="tests"></a>
# 7. 🧪 Tests et validation

## Tests automatisés

### Lancer tous les tests

```bash
# Depuis la racine du projet
python test_auth.py
```

### Résultat attendu

```
🧪 Test du système d'authentification HorRAGor

✅ 1. Health check réussi
   API accessible sur http://localhost:8000

✅ 2. Inscription réussie
   Email: test_Dy8k2@example.com
   Username: testuser_Dy8k2
   User ID: 42

✅ 3. Récupération du profil réussie
   Username: testuser_Dy8k2
   Email: test_Dy8k2@example.com
   Actif: True

✅ 4. Rafraîchissement des tokens réussi
   Nouveaux tokens générés

✅ 5. Connexion réussie
   Access token valide
   Refresh token valide

✅ 6. Déconnexion réussie
   Token révoqué

🎉 Tous les tests sont passés !
   - 6/6 tests réussis
   - Durée: 3.2s
```

## Tests manuels via Swagger UI

### Ouvrir Swagger

1. Démarrer l'API : `cd api && uv run uvicorn main:app --reload`
2. Ouvrir http://localhost:8000/docs

### Test 1 : Inscription

1. Cliquer sur `POST /auth/register`
2. Cliquer sur "Try it out"
3. Remplir le JSON :
```json
{
  "email": "test@example.com",
  "username": "testuser",
  "password": "Password123!"
}
```
4. Cliquer sur "Execute"
5. Vérifier la réponse 201 avec les tokens

### Test 2 : Connexion

1. Cliquer sur `POST /auth/login`
2. Cliquer sur "Try it out"
3. Remplir :
```json
{
  "email": "test@example.com",
  "password": "Password123!"
}
```
4. Cliquer sur "Execute"
5. Copier l'`access_token` de la réponse

### Test 3 : Route protégée

1. Cliquer sur le cadenas 🔒 en haut à droite
2. Coller le token : `Bearer <access_token>`
3. Cliquer sur "Authorize"
4. Cliquer sur `GET /auth/me`
5. Cliquer sur "Try it out" puis "Execute"
6. Vérifier que le profil est retourné

### Test 4 : Rafraîchissement

1. Copier le `refresh_token` de l'inscription/connexion
2. Cliquer sur `POST /auth/refresh`
3. Remplir :
```json
{
  "refresh_token": "<votre_refresh_token>"
}
```
4. Cliquer sur "Execute"
5. Vérifier que de nouveaux tokens sont générés

### Test 5 : Déconnexion

1. Cliquer sur `POST /auth/logout`
2. Remplir avec le refresh_token
3. Cliquer sur "Execute"
4. Vérifier la réponse 200
5. Tenter de réutiliser le token → Erreur 401

## Tests manuels via l'interface Streamlit

### Test 1 : Inscription

1. Ouvrir http://localhost:8501
2. Onglet "Inscription"
3. Remplir :
   - Email : `user1@test.com`
   - Username : `user1`
   - Password : `TestPass123!`
4. Cliquer sur "Créer un compte"
5. **Vérification** : Redirection automatique vers l'app

### Test 2 : Déconnexion

1. Cliquer sur "🚪 Se déconnecter" dans la sidebar
2. **Vérification** : Retour sur la page de connexion

### Test 3 : Connexion

1. Onglet "Connexion"
2. Remplir :
   - Email : `user1@test.com`
   - Password : `TestPass123!`
3. Cliquer sur "Se connecter"
4. **Vérification** : Accès à l'application

### Test 4 : Session persistante

1. Se connecter
2. Interagir avec l'application (poser des questions)
3. Rafraîchir la page (F5)
4. **Vérification** : Toujours connecté (pas de redirection vers login)

### Test 5 : Tokens expirés

1. Se connecter
2. Attendre 30 minutes (ou modifier `ACCESS_TOKEN_EXPIRE_MINUTES` à 1)
3. Faire une action dans l'app
4. **Vérification** : Rafraîchissement automatique des tokens

## Tests de sécurité

### Test 1 : Injection SQL

```bash
# Tenter une injection dans l'email
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com; DROP TABLE users;--",
    "username": "testuser",
    "password": "Password123!"
  }'
```

**Résultat attendu** : Erreur de validation Pydantic (email invalide)

### Test 2 : Brute force

```bash
# Tenter plusieurs connexions
for i in {1..100}; do
  curl -X POST "http://localhost:8000/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email": "test@example.com", "password": "wrong'$i'"}'
done
```

**Résultat attendu** : 
- Toutes les requêtes retournent 401
- Le hash bcrypt ralentit naturellement les tentatives

**Amélioration recommandée** : Ajouter un rate limiter

### Test 3 : Token forgé

```python
# Créer un faux token
import jwt

fake_token = jwt.encode(
    {"sub": 999, "email": "fake@example.com"},
    "wrong-secret-key",
    algorithm="HS256"
)

# Tenter de l'utiliser
response = requests.get(
    "http://localhost:8000/auth/me",
    headers={"Authorization": f"Bearer {fake_token}"}
)

print(response.status_code)  # 401
```

**Résultat attendu** : 401 Unauthorized

### Test 4 : Token expiré

```python
from datetime import datetime, timedelta
import jwt
from api.auth_config import JWT_SECRET_KEY, JWT_ALGORITHM

# Créer un token expiré
expired_token = jwt.encode(
    {
        "sub": 1,
        "email": "test@example.com",
        "exp": datetime.utcnow() - timedelta(hours=1)  # Expiré il y a 1h
    },
    JWT_SECRET_KEY,
    algorithm=JWT_ALGORITHM
)

# Tenter de l'utiliser
response = requests.get(
    "http://localhost:8000/auth/me",
    headers={"Authorization": f"Bearer {expired_token}"}
)

print(response.status_code)  # 401
```

**Résultat attendu** : 401 Unauthorized

## Validation en base de données

### Vérifier les tables

```sql
-- Connexion à Supabase via SQL Editor

-- 1. Vérifier la table users
SELECT * FROM users LIMIT 5;

-- 2. Vérifier la table refresh_tokens
SELECT * FROM refresh_tokens LIMIT 5;

-- 3. Compter les utilisateurs
SELECT COUNT(*) FROM users;

-- 4. Compter les tokens actifs
SELECT COUNT(*) FROM refresh_tokens WHERE is_revoked = FALSE;

-- 5. Vérifier les tokens expirés
SELECT COUNT(*) FROM refresh_tokens WHERE expires_at < NOW();
```

### Vérifier les contraintes

```sql
-- Tenter d'insérer un email dupliqué (doit échouer)
INSERT INTO users (email, username, hashed_password)
VALUES ('existing@example.com', 'newuser', 'hash');
-- Erreur : duplicate key value violates unique constraint "users_email_key"

-- Tenter d'insérer un refresh_token avec user_id inexistant (doit échouer)
INSERT INTO refresh_tokens (token, user_id, expires_at)
VALUES ('fake-token', 9999, NOW() + INTERVAL '7 days');
-- Erreur : insert or update on table "refresh_tokens" violates foreign key constraint
```

## Checklist de validation complète

### ✅ Backend

- [ ] Tables `users` et `refresh_tokens` créées
- [ ] Les 6 endpoints `/auth/*` sont accessibles
- [ ] Swagger UI affiche la documentation
- [ ] Health check retourne 200
- [ ] Inscription crée un utilisateur en DB
- [ ] Inscription retourne access_token et refresh_token
- [ ] Connexion avec credentials valides retourne tokens
- [ ] Connexion avec credentials invalides retourne 401
- [ ] `/auth/me` sans token retourne 401
- [ ] `/auth/me` avec token valide retourne le profil
- [ ] `/auth/refresh` avec token valide génère de nouveaux tokens
- [ ] `/auth/logout` révoque le refresh_token
- [ ] Token révoqué ne peut plus être utilisé

### ✅ Frontend

- [ ] Page de connexion s'affiche au démarrage
- [ ] Formulaire d'inscription valide les champs
- [ ] Inscription réussie redirige vers l'app
- [ ] Formulaire de connexion valide les champs
- [ ] Connexion réussie redirige vers l'app
- [ ] Bouton de déconnexion apparaît dans la sidebar
- [ ] Déconnexion redirige vers la page de connexion
- [ ] Session persiste après F5
- [ ] Application est inaccessible sans connexion

### ✅ Sécurité

- [ ] Mots de passe hashés avec bcrypt
- [ ] Tokens JWT signés avec clé secrète
- [ ] Tokens contiennent une expiration
- [ ] Refresh tokens stockés en base de données
- [ ] Refresh tokens peuvent être révoqués
- [ ] Routes protégées nécessitent un Bearer token
- [ ] Token invalide/expiré retourne 401
- [ ] Email dupliqué retourne 400
- [ ] Username dupliqué retourne 400

### ✅ Documentation

- [ ] README mis à jour
- [ ] Swagger UI complète et à jour
- [ ] Exemples de code fournis
- [ ] Guide d'installation disponible
- [ ] Guide de déploiement disponible

---

<a name="integration"></a>
# 8. 🔗 Intégration avec les EPICs futurs

## EPIC 2 : Gestion de la mémoire utilisateur (Langmem)

### Impact de EPIC 10

✅ **Prérequis satisfait** : L'authentification permet de lier les mémoires aux utilisateurs.

### Modifications nécessaires

#### 1. Créer la table `user_memories`

```python
# database/tables/user_memories.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database.tables.base import Base

class UserMemory(Base):
    """Table de mémoire utilisateur pour Langmem."""
    __tablename__ = "user_memories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    memory_key = Column(String(255), nullable=False)  # Ex: "favorite_genre"
    memory_value = Column(Text, nullable=False)  # Ex: "Gore, Slasher"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relation avec User
    user = relationship("User", back_populates="memories")
```

#### 2. Modifier le modèle `User`

```python
# database/tables/users.py (ajouter)
from sqlalchemy.orm import relationship

class User(Base):
    # ... champs existants ...
    
    # ⚠️ AJOUTER
    memories = relationship("UserMemory", back_populates="user", cascade="all, delete-orphan")
```

#### 3. Créer les endpoints de mémoire

```python
# api/memory_routes.py
from fastapi import APIRouter, Depends
from api.auth_utils import get_current_user
from database.models import User, UserMemory

router = APIRouter(prefix="/memory", tags=["Memory"])

@router.get("/")
async def get_user_memories(current_user: User = Depends(get_current_user)):
    """Récupère toutes les mémoires de l'utilisateur."""
    return [
        {"key": mem.memory_key, "value": mem.memory_value}
        for mem in current_user.memories
    ]

@router.post("/")
async def save_memory(
    key: str,
    value: str,
    current_user: User = Depends(get_current_user)
):
    """Sauvegarde une mémoire."""
    from database.connection import get_db
    
    db = next(get_db())
    
    # Chercher si la mémoire existe
    memory = db.query(UserMemory).filter(
        UserMemory.user_id == current_user.id,
        UserMemory.memory_key == key
    ).first()
    
    if memory:
        # Mettre à jour
        memory.memory_value = value
    else:
        # Créer
        memory = UserMemory(
            user_id=current_user.id,
            memory_key=key,
            memory_value=value
        )
        db.add(memory)
    
    db.commit()
    return {"message": "Memory saved"}
```

### Utilisation dans les agents

```python
# agents/nodes.py (modifier)
async def narrator_node(state: AgentState) -> AgentState:
    """Nœud narrateur avec mémoire utilisateur."""
    user_id = state.get("user_id")
    
    if user_id:
        # Récupérer les mémoires de l'utilisateur
        from database.connection import get_db
        from database.models import UserMemory
        
        db = next(get_db())
        memories = db.query(UserMemory).filter(UserMemory.user_id == user_id).all()
        
        # Construire le contexte de mémoire
        memory_context = "\n".join([
            f"- {mem.memory_key}: {mem.memory_value}"
            for mem in memories
        ])
        
        # Inclure dans le prompt
        prompt = f"""
        Tu es un narrateur gothique.
        
        Mémoires de l'utilisateur :
        {memory_context}
        
        Utilise ces informations pour personnaliser ta réponse.
        
        Question : {state['query']}
        """
    else:
        # Mode sans authentification (à supprimer en production)
        prompt = state['query']
    
    # ... reste de la logique
```

## EPIC 3 : Gestion Intent

### Impact de EPIC 10

✅ **Bénéfice** : Chaque utilisateur peut avoir un historique d'intent personnalisé.

### Modifications nécessaires

#### 1. Modifier `AgentState`

```python
# agents/state.py (ajouter)
from typing import TypedDict, Optional, List

class AgentState(TypedDict):
    # Champs existants
    query: str
    filters: Optional[dict]
    messages: List[dict]
    # ... autres champs
    
    # ⚠️ NOUVEAUX CHAMPS
    user_id: Optional[int]  # Pour lier à l'utilisateur
    conversation_history: Optional[List[dict]]  # Historique des échanges
```

#### 2. Modifier les routes `/chat`

```python
# api/routes.py (modifier)
from api.auth_utils import get_current_user

@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)  # ⚠️ AJOUTER
):
    """Endpoint de chat avec authentification."""
    
    # Construire l'état initial
    initial_state = {
        "query": request.query,
        "filters": request.filters,
        "user_id": current_user.id,  # ⚠️ AJOUTER
        # ... autres champs
    }
    
    # Récupérer l'historique de conversation
    # (à implémenter avec EPIC 2 ou table dédiée)
    from database.connection import get_db
    from database.models import UserMemory
    
    db = next(get_db())
    history_mem = db.query(UserMemory).filter(
        UserMemory.user_id == current_user.id,
        UserMemory.memory_key == "conversation_history"
    ).first()
    
    if history_mem:
        import json
        initial_state["conversation_history"] = json.loads(history_mem.memory_value)
    
    # Exécuter le graphe
    result = await graph.ainvoke(initial_state)
    
    return result
```

## EPIC 4 : Carte Film

### Impact de EPIC 10

✅ **Aucune dépendance** : Travail totalement indépendant.

⚠️ **Optionnel** : Peut intégrer l'user_id pour personnaliser l'affichage.

### Exemples d'intégration

```python
# frontend/components/components.py
def display_movie_card(movie: dict):
    """Affiche une carte de film personnalisée."""
    user = st.session_state.get("user")
    
    # Affichage standard
    st.markdown(f"### {movie['title']}")
    st.markdown(f"**Synopsis** : {movie.get('synopsis', 'Non disponible')}")
    
    # Personnalisation si utilisateur connecté
    if user:
        # Récupérer les préférences utilisateur
        preferences = get_user_preferences(user['id'])
        
        # Afficher si le film correspond aux préférences
        if movie['genre'] in preferences.get('favorite_genres', []):
            st.success("💚 Ce film correspond à vos goûts !")
```

## EPIC 5 : Séparation des agents (SoC)

### Impact de EPIC 10

✅ **Aucun impact direct**, mais bénéficie de `user_id` si EPIC 3 est fait.

### Point d'attention

Si EPIC 3 est fait avant EPIC 5, penser à propager `user_id` dans tous les agents :

```python
# agents/rag_agent/nodes.py
def rag_search_node(state: AgentState) -> AgentState:
    """Recherche RAG avec contexte utilisateur."""
    user_id = state.get("user_id")
    
    # Personnaliser la recherche selon l'utilisateur
    if user_id:
        # Récupérer les films déjà vus
        # Prioriser les films non vus
        pass
    
    # ... logique RAG normale
```

## EPIC 6 : Langfuse

### Impact de EPIC 10

✅ **Excellent** : Les traces peuvent être liées aux utilisateurs.

### Modifications nécessaires

```python
# api/routes.py (modifier)
from langfuse import Langfuse
from langfuse.decorators import observe

langfuse = Langfuse()

@router.post("/chat")
@observe(name="chat_endpoint")  # Décorateur Langfuse
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """Endpoint de chat avec tracing Langfuse."""
    
    # Créer une trace Langfuse avec user_id
    trace = langfuse.trace(
        name="chat_session",
        user_id=str(current_user.id),  # ⚠️ Lier à l'utilisateur
        metadata={
            "username": current_user.username,
            "email": current_user.email
        }
    )
    
    # Exécuter le graphe avec callbacks Langfuse
    result = await graph.ainvoke(
        initial_state,
        config={"callbacks": [trace]}
    )
    
    return result
```

**Avantages** :
- Traces par utilisateur dans Langfuse UI
- Analyse de l'usage par utilisateur
- Détection d'anomalies par utilisateur

## EPIC 7 : Docker

### Impact de EPIC 10

⚠️ **Modifications requises** : Ajouter les variables JWT dans Docker Compose.

### Modifications nécessaires

```yaml
# docker-compose.yml (modifier)
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    environment:
      # Variables existantes
      - SUPABASE_HOST=${SUPABASE_HOST}
      - SUPABASE_USER=${SUPABASE_USER}
      - SUPABASE_PASSWORD=${SUPABASE_PASSWORD}
      - SUPABASE_DB=${SUPABASE_DB}
      - SUPABASE_PORT=${SUPABASE_PORT}
      
      # ⚠️ NOUVELLES VARIABLES EPIC 10
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - JWT_ALGORITHM=${JWT_ALGORITHM}
      - ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES}
      - REFRESH_TOKEN_EXPIRE_DAYS=${REFRESH_TOKEN_EXPIRE_DAYS}
      
      # Variables Langfuse (EPIC 6)
      - LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY}
      - LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY}
    ports:
      - "8000:8000"
    depends_on:
      - langfuse
  
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    environment:
      - API_HOST=api
      - API_PORT=8000
    ports:
      - "8501:8501"
    depends_on:
      - api
  
  langfuse:
    image: langfuse/langfuse:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/langfuse
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=langfuse
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Fichier .env pour Docker

```bash
# .env.docker
# Base de données Supabase
SUPABASE_HOST=your-project.supabase.co
SUPABASE_USER=postgres
SUPABASE_PASSWORD=your-password
SUPABASE_DB=postgres
SUPABASE_PORT=5432

# JWT (IMPORTANT : Changer en production !)
JWT_SECRET_KEY=your-production-secret-key-change-this
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Langfuse
LANGFUSE_PUBLIC_KEY=your-langfuse-public-key
LANGFUSE_SECRET_KEY=your-langfuse-secret-key
```

## EPIC 8 : CI/CD

### Impact de EPIC 10

✅ **Positif** : Documentation déjà complète, tests déjà créés.

### À intégrer

```yaml
# .github/workflows/ci.yml
name: CI/CD HorRAGor

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd api
          pip install uv
          uv sync
      
      - name: Run auth tests
        run: |
          python test_auth.py
        env:
          JWT_SECRET_KEY: ${{ secrets.JWT_SECRET_KEY }}
          SUPABASE_HOST: ${{ secrets.SUPABASE_HOST }}
          # ... autres secrets
  
  security:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Check vulnerabilities
        run: |
          pip install safety bandit
          safety check
          bandit -r api/ database/ agents/
  
  build-docker:
    needs: [test, security]
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - uses: docker/build-push-action@v4
        with:
          context: .
          file: Dockerfile.api
          push: true
          tags: horragor:latest
```

## EPIC 9 : Affichage progression

### Impact de EPIC 10

✅ **Aucun impact direct**, mais peut personnaliser l'affichage.

### Exemple d'intégration

```python
# frontend/app.py
def display_agent_progress():
    """Affiche la progression des agents."""
    user = st.session_state.get("user")
    
    # Conteneur de progression
    progress_container = st.empty()
    
    # Stream des événements
    for event in stream_chat_response(query, user['id'] if user else None):
        if event["type"] == "agent_step":
            # Afficher l'étape avec personnalisation
            icon = "🔍" if event["agent"] == "RAG" else "🕸️" if event["agent"] == "Scraper" else "✍️"
            progress_container.info(f"{icon} {event['agent']} : {event['message']}")
        
        elif event["type"] == "completion":
            progress_container.success("✅ Terminé !")
            
            # Si utilisateur connecté, sauvegarder dans l'historique
            if user:
                save_to_history(user['id'], event['result'])
```

---

<a name="manifest"></a>
# 9. 📋 Fichiers modifiés et créés

## Nouveaux fichiers (18)

### Database (3 fichiers)

1. **database/tables/users.py** (57 lignes)
   - Modèle SQLAlchemy pour la table `users`
   - Colonnes : id, email, username, hashed_password, is_active, is_verified, created_at, updated_at

2. **database/tables/refresh_tokens.py** (45 lignes)
   - Modèle SQLAlchemy pour la table `refresh_tokens`
   - Colonnes : id, token, user_id (FK), expires_at, is_revoked, created_at

3. **database/create_auth_tables.py** (68 lignes)
   - Script de migration pour créer les tables d'authentification
   - Utilise SQLAlchemy pour créer les tables

### API Backend (3 fichiers)

4. **api/auth_config.py** (32 lignes)
   - Configuration JWT (secret key, algorithme, durées d'expiration)
   - Chargement des variables d'environnement

5. **api/auth_utils.py** (288 lignes)
   - 9 fonctions utilitaires d'authentification
   - hash_password(), verify_password()
   - create_access_token(), create_refresh_token()
   - decode_access_token(), validate_refresh_token()
   - authenticate_user(), get_current_user()
   - revoke_refresh_token(), revoke_all_user_tokens()

6. **api/auth_routes.py** (345 lignes)
   - 6 endpoints d'authentification
   - POST /auth/register, POST /auth/login
   - POST /auth/refresh, POST /auth/logout
   - POST /auth/logout-all, GET /auth/me

### Frontend (2 fichiers)

7. **frontend/utils/auth_client.py** (187 lignes)
   - Client API pour l'authentification
   - 5 fonctions : login_user(), register_user(), refresh_access_token(), logout_user(), get_current_user()

8. **frontend/components/auth_components.py** (298 lignes)
   - Composants UI Streamlit pour l'authentification
   - 5 fonctions : check_authentication(), logout_button(), render_login_page(), render_login_form(), render_register_form()

### Tests et Scripts (3 fichiers)

9. **test_auth.py** (224 lignes)
   - Suite de tests complète pour l'authentification
   - 6 tests : health check, inscription, profil, refresh, login, logout

10. **start.py** (185 lignes)
    - Script Python de démarrage automatique
    - Orchestre la création des tables, installation des dépendances, démarrage API/frontend

11. **start_with_auth.sh** (98 lignes)
    - Script Bash de démarrage (Linux/Mac)
    - Équivalent de start.py en shell

12. **start_with_auth.bat** (87 lignes)
    - Script Batch de démarrage (Windows)
    - Équivalent de start.py en batch

### Documentation (7 fichiers - maintenant 1 seul)

13-19. **EPIC10_DOCUMENTATION_COMPLETE.md** (ce fichier)
    - Documentation complète consolidée
    - Remplace les 11 fichiers .md précédents

## Fichiers modifiés (6)

### Database (1 fichier)

1. **database/models.py**
   - Ajout de 2 imports : `from database.tables.users import User`
   - `from database.tables.refresh_tokens import RefreshToken`

### API Backend (3 fichiers)

2. **api/main.py**
   - Ajout de l'import : `from api.auth_routes import router as auth_router`
   - Ajout de : `app.include_router(auth_router)`

3. **api/schemas.py**
   - Ajout de 6 schémas Pydantic :
     - UserRegister, UserLogin, Token, TokenRefresh, UserResponse, AuthResponse

4. **api/pyproject.toml**
   - Ajout de 2 dépendances :
     - `passlib[bcrypt]>=1.7.4`
     - `python-jose[cryptography]>=3.3.0`

### Frontend (1 fichier)

5. **frontend/app.py**
   - Ajout des imports : `from components.auth_components import check_authentication, render_login_page, logout_button`
   - Ajout de la vérification d'authentification au début de `main()`
   - Ajout de `logout_button()` dans la sidebar

### Configuration (1 fichier)

6. **.env.example**
   - Ajout de la section "JWT Configuration"
   - 4 nouvelles variables : JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

## Statistiques

### Code source
- **Nouveaux fichiers** : 18
- **Fichiers modifiés** : 6
- **Total lignes ajoutées** : ~2750

### Dépendances
- **Packages Python ajoutés** : 2 directs (passlib, python-jose)
- **Dépendances transitives** : 88
- **Total installé** : 90 packages

### Base de données
- **Nouvelles tables** : 2 (users, refresh_tokens)
- **Nouvelles colonnes** : 15 au total

### Documentation
- **Documents créés** : 1 (consolidé)
- **Lignes de documentation** : ~4500

---

<a name="troubleshooting"></a>
# 10. 🔧 Troubleshooting

## Erreurs d'installation

### Erreur : "ModuleNotFoundError: No module named 'passlib'"

**Cause** : Dépendances non installées

**Solution** :
```bash
cd api
uv sync --force
```

### Erreur : "Could not find a version that matches passlib[bcrypt]"

**Cause** : Version UV obsolète ou cache corrompu

**Solution** :
```bash
# Mettre à jour UV
pip install --upgrade uv

# Nettoyer le cache
uv cache clean

# Réinstaller
uv sync
```

### Erreur : "python-jose[cryptography] requires cryptography"

**Cause** : cryptography nécessite des outils de compilation

**Solution Windows** :
```bash
# Installer Microsoft C++ Build Tools
# https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

**Solution Linux** :
```bash
sudo apt-get install build-essential libssl-dev libffi-dev python3-dev
```

**Solution Mac** :
```bash
xcode-select --install
```

## Erreurs de base de données

### Erreur : "could not connect to server: Connection refused"

**Cause** : Credentials Supabase incorrects ou base inaccessible

**Solution** :
1. Vérifier `.env` :
```bash
cat .env | grep SUPABASE
```

2. Tester la connexion :
```python
python -c "
from database.connection import engine
try:
    conn = engine.connect()
    print('✅ Connexion réussie')
except Exception as e:
    print(f'❌ Erreur: {e}')
"
```

3. Vérifier dans Supabase Dashboard :
   - Settings > Database > Connection string
   - Copier les valeurs dans `.env`

### Erreur : "relation 'users' does not exist"

**Cause** : Tables non créées

**Solution** :
```bash
cd database
python create_auth_tables.py
```

**Vérification** :
```sql
-- Dans Supabase SQL Editor
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
```

### Erreur : "duplicate key value violates unique constraint 'users_email_key'"

**Cause** : Email déjà utilisé

**Solution** :
```python
# Utiliser un autre email ou supprimer l'utilisateur existant
# Dans Supabase SQL Editor :
DELETE FROM users WHERE email = 'test@example.com';
```

## Erreurs JWT

### Erreur : "JWT_SECRET_KEY not found"

**Cause** : Variable d'environnement non chargée

**Solution** :
1. Vérifier que `.env` existe :
```bash
ls -la .env
```

2. Vérifier que la variable est définie :
```bash
cat .env | grep JWT_SECRET_KEY
```

3. Redémarrer l'API :
```bash
cd api
uv run uvicorn main:app --reload
```

### Erreur : "Invalid or expired token"

**Cause** : Token expiré ou invalide

**Solution** :
```python
# Se reconnecter pour obtenir un nouveau token
# Ou utiliser le refresh token :
import requests

response = requests.post(
    "http://localhost:8000/auth/refresh",
    json={"refresh_token": "votre_refresh_token"}
)

new_tokens = response.json()
```

### Erreur : "Token signature verification failed"

**Cause** : JWT_SECRET_KEY a changé ou token forgé

**Solution** :
```bash
# Vérifier que JWT_SECRET_KEY n'a pas changé
cat .env | grep JWT_SECRET_KEY

# Se reconnecter pour obtenir un nouveau token
```

## Erreurs d'authentification

### Erreur : "Invalid credentials"

**Cause** : Email ou mot de passe incorrect

**Solution** :
```python
# Vérifier l'email en base :
# Dans Supabase SQL Editor :
SELECT email, username FROM users WHERE email = 'test@example.com';

# Réinitialiser le mot de passe (à implémenter) ou créer un nouveau compte
```

### Erreur : "User not found or inactive"

**Cause** : Utilisateur désactivé ou supprimé

**Solution** :
```sql
-- Réactiver l'utilisateur
UPDATE users SET is_active = TRUE WHERE email = 'test@example.com';
```

### Erreur : "Refresh token not found or revoked"

**Cause** : Token déjà utilisé ou révoqué

**Solution** :
```python
# Se reconnecter pour obtenir de nouveaux tokens
import requests

response = requests.post(
    "http://localhost:8000/auth/login",
    json={
        "email": "test@example.com",
        "password": "votre_mot_de_passe"
    }
)

tokens = response.json()
```

## Erreurs Frontend

### Erreur : "StreamlitAPIException: set_page_config() can only be called once"

**Cause** : Conflit de configuration Streamlit

**Solution** :
```python
# Dans frontend/app.py, s'assurer que set_page_config() est appelé une seule fois
# Et en tout premier (avant tout autre appel Streamlit)

import streamlit as st

# ✅ Bon : En premier
st.set_page_config(page_title="HorRAGor", layout="wide")

# Reste du code...
```

### Erreur : "Connection refused" lors de l'appel API

**Cause** : API non démarrée

**Solution** :
```bash
# Démarrer l'API dans un terminal séparé
cd api
uv run uvicorn main:app --reload
```

### Page de connexion ne s'affiche pas

**Cause** : Import manquant ou erreur dans auth_components.py

**Solution** :
```python
# Vérifier les imports dans app.py
from components.auth_components import check_authentication, render_login_page

# Vérifier que la fonction est appelée
if not check_authentication():
    render_login_page()
    return
```

## Erreurs de session

### Session perdue après F5

**Cause** : session_state non persisté

**Solution** :
```python
# La session Streamlit persiste automatiquement
# Si problème, vérifier que les tokens sont bien stockés :

# Dans auth_components.py après connexion réussie :
st.session_state["access_token"] = response["access_token"]
st.session_state["refresh_token"] = response["refresh_token"]
st.session_state["user"] = response["user"]
```

### Déconnexion intempestive

**Cause** : Token expiré sans rafraîchissement

**Solution** :
```python
# Implémenter le rafraîchissement automatique dans auth_client.py
def api_call_with_refresh(url, **kwargs):
    access_token = st.session_state.get("access_token")
    
    response = requests.request(url, headers={"Authorization": f"Bearer {access_token}"}, **kwargs)
    
    if response.status_code == 401:
        # Rafraîchir
        refresh_token = st.session_state.get("refresh_token")
        new_tokens = refresh_access_token(refresh_token)
        
        # Réessayer
        response = requests.request(url, headers={"Authorization": f"Bearer {new_tokens['access_token']}"}, **kwargs)
    
    return response
```

## Erreurs de production

### "Secret key is insecure"

**Cause** : Utilisation de la clé par défaut

**Solution** :
```bash
# Générer une nouvelle clé
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Mettre à jour .env
JWT_SECRET_KEY=la-nouvelle-cle-generee

# Redémarrer l'API
```

### "CORS error" lors d'appels API

**Cause** : CORS non configuré

**Solution** :
```python
# Dans api/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Frontend Streamlit
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Commandes de diagnostic

### Vérifier l'état de l'installation

```bash
# Backend
cd api
uv run python -c "
from api.auth_utils import hash_password
from database.models import User, RefreshToken
print('✅ Imports OK')
"

# Frontend
cd frontend
python -c "
from utils.auth_client import login_user
from components.auth_components import render_login_page
print('✅ Imports OK')
"
```

### Tester la connexion base de données

```bash
python -c "
from database.connection import engine
from database.models import User

# Connexion
conn = engine.connect()
print('✅ Connexion réussie')

# Compter les users
from sqlalchemy import select
stmt = select(User)
result = conn.execute(stmt)
print(f'Nombre d\'utilisateurs : {len(result.fetchall())}')

conn.close()
"
```

### Vérifier les tokens

```python
from api.auth_utils import create_access_token, decode_access_token

# Créer un token de test
token = create_access_token({"sub": 1, "email": "test@example.com"})
print(f"Token créé : {token[:50]}...")

# Le décoder
payload = decode_access_token(token)
print(f"Payload : {payload}")
```

---

# 🎊 Félicitations !

Vous avez maintenant un système d'authentification complet et sécurisé pour HorRAGor ! 🚀

## Points clés à retenir

✅ **Sécurité** : Hash bcrypt, JWT signé, refresh tokens révocables  
✅ **Fonctionnalités** : Inscription, connexion, rafraîchissement, déconnexion  
✅ **Protection** : Application et API sécurisées  
✅ **Documentation** : Complète et accessible  
✅ **Tests** : Suite de tests automatisés  
✅ **Intégration** : Prêt pour les EPICs suivants  

## Prochaines étapes

1. **Tester le système** : `python test_auth.py`
2. **Démarrer l'application** : `python start.py`
3. **Créer un compte** : Ouvrir http://localhost:8501
4. **Continuer avec EPIC 2** : Langmem pour la mémoire utilisateur

## Support

- 📚 Cette documentation
- 🔍 Code source commenté
- 🧪 Tests automatisés
- 📊 Swagger UI : http://localhost:8000/docs

---

**HorRAGor est maintenant un chatbot d'horreur sécurisé et professionnel !** 👻🔐

**Bon développement ! 🚀**
