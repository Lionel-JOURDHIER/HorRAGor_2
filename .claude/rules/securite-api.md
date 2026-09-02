---
paths:
  - "src/api/**/*.py"
  - "**/routes/**/*.py"
  - "**/auth.py"
  - "**/security.py"
---

# Sécurité d'une API

<!-- Portée à ajuster à l'arborescence réelle : cette règle ne doit se charger
     que sur le code qui expose ou protège des routes. Chargée partout, elle
     coûte du contexte à chaque session pour rien.

     Source : kit de formation « Sécuriser une API FastAPI » (OWASP API Top 10,
     OAuth2, JWT, refresh tokens) et ses six ateliers. -->

Une API authentifiée n'est pas une API sûre. L'authentification (qui vous êtes)
est la porte d'entrée ; l'autorisation, la consommation et la configuration
ferment les trois autres. Les règles ci-dessous couvrent les entrées de l'OWASP
API Top 10 qu'on rencontre réellement : API2 (authentification cassée), API5
(autorisation de fonction), API4 (consommation sans limite), API8 (mauvaise
configuration).

## Mots de passe

- Jamais en clair, jamais un hash rapide (`hashlib.sha256`, `md5`) même salé à
  la main : ils sont conçus pour être rapides, donc pour être forcés vite.
- **pwdlib avec bcrypt**, l'algorithme est lent par conception et sale
  automatiquement — deux mots de passe identiques donnent deux empreintes
  différentes, ce qui neutralise les tables pré-calculées.

  ```python
  from pwdlib import PasswordHash
  from pwdlib.hashers.bcrypt import BcryptHasher

  password_hash = PasswordHash((BcryptHasher(),))
  ```

- Ne pas remplacer par `passlib` : non maintenu, `pwdlib` en est le successeur.

## Chiffrement des données

Le hachage est à sens unique, le chiffrement est réversible : ce ne sont pas des
outils interchangeables. Un mot de passe se hache, une donnée qu'il faudra relire
se chiffre.

- Symétrique : `cryptography.Fernet` — AES avec authentification intégrée, donc
  un message modifié est rejeté et pas déchiffré en silence. Ne pas assembler
  soi-même un mode AES.
- Asymétrique : `cryptography` RSA, clé de **2048 bits minimum**, padding
  **OAEP**. Le padding brut (`PKCS#1 v1.5`, ou pire aucun) est attaquable et
  rend le chiffrement déterministe.
- Les clés vivent hors du code et hors du dépôt, au même endroit que les autres
  secrets, avec la même règle d'échec au démarrage. Une clé perdue rend les
  données irrécupérables : sa sauvegarde fait partie du projet, pas de
  l'exploitation.

## JWT

Un JWT est **signé, pas chiffré** : n'importe qui le lit. Rien de sensible dans
le payload — ni mot de passe, ni donnée personnelle, ni secret métier.

- **Épingler l'algorithme au décodage** : `algorithms=["HS256"]`, une seule
  valeur. Une liste mixte rouvre la confusion d'algorithme ; l'absence de liste
  rouvre `alg:none`.
- Vérifier explicitement `audience=` et `issuer=`. Un claim non passé en
  paramètre n'est **pas** vérifié, même s'il est présent dans le token — c'est
  le piège le plus courant.
- Claims obligatoires déclarés, `aud`/`iss`/`nbf` inclus dès que le projet les
  émet — les déclarer requis sans aussi les vérifier via `audience=`/`issuer=`
  ne sert à rien, et les vérifier sans les rendre requis laisse passer un
  token qui les omet purement et simplement :
  `options={"require": ["exp", "iat", "nbf", "iss", "aud", "sub"]}`.
- Signature asymétrique (RS256) : la clé de vérification est publique, donc
  connue d'un attaquant. Sans épinglage, il forge un HS256 en utilisant cette
  clé publique comme secret HMAC.
- Ne jamais décoder avec `verify_signature: False` en dehors d'un outil de
  diagnostic explicitement nommé comme tel.
- Le paquet à installer est `pyjwt`, l'import reste `import jwt` — un
  `ModuleNotFoundError: jwt` vient presque toujours d'un `pip install jwt`
  (mauvais paquet) au lieu de `pyjwt`.

## Sessions : access + refresh

- **Authorization Code + PKCE** plutôt que Resource Owner Password Grant pour
  obtenir ces jetons : le client ne voit jamais le mot de passe de
  l'utilisateur, seulement un code d'échange redirigé par le fournisseur
  d'identité. Le tutoriel officiel FastAPI (`OAuth2PasswordRequestForm`, champ
  `username`/`password` posté directement à l'API) enseigne justement le grant
  mot de passe — à réserver à un script interne au dépôt (tests, outillage
  d'administration), jamais à un client tiers ou une application publique.
- `OAuth2PasswordRequestForm` (FastAPI) lit `username`/`password` depuis un
  formulaire, pas du JSON : dépend de `python-multipart`, absent par défaut.
  Un `422` sur `/token` sans autre message vient presque toujours de là.
- Service à service, sans utilisateur humain (un agent interne qui appelle une
  autre API du même système) : grant **Client Credentials**, pas Password
  Grant ni Authorization Code — il n'y a personne à qui déléguer un
  consentement.
- **Access court** (~15 min) et **refresh long** (~7 j), distingués par un claim
  `type`. Un refresh présenté à la place d'un access est refusé, et
  réciproquement.
- **Rotation à chaque `/refresh`** : l'ancien jeton est révoqué, un nouveau
  émis. Rejouer un refresh déjà tourné est refusé.
- Révocation : un `jti` unique par refresh et un ensemble des `jti` encore
  valides. **En production, cet état va en Redis ou en base** — en mémoire, la
  révocation ne survit ni à un redémarrage ni à un second serveur, et le logout
  devient décoratif.
- Le logout ne révoque que le refresh : un access déjà émis reste valide jusqu'à
  son expiration. C'est la raison pour laquelle l'access doit être court, et il
  faut le dire au métier plutôt que de promettre une déconnexion instantanée.
- Détection de vol par familles (un rejeu révoque toute la session en cascade) :
  seulement si le vol de session est un risque identifié du projet. Sinon
  `jti` + rotation + révocation au logout suffisent — ne pas sur-construire.

## Autorisation

- **401 ≠ 403.** 401 : identité non prouvée. 403 : identité connue, droits
  insuffisants. La confusion des deux masque les vrais problèmes de droits.
- Routes protégées par `Depends(get_current_user)` : sans jeton valide, la
  fonction n'est jamais exécutée. Le `401` levé porte l'en-tête
  `headers={"WWW-Authenticate": "Bearer"}`, exigé par la spécification HTTP
  pour ce code — pas décoratif, un client standard s'y attend.
- Contrôle de rôle par **dépendances chaînées** (`require_admin` dépend de
  `get_current_user`), pas par un `if` en début de fonction : le contrôle se voit
  dans la signature et ne peut pas être oublié dans une nouvelle route.

## Configuration : fail-closed

Une configuration manquante arrête le démarrage. Une valeur par défaut
silencieuse est une faille : une `SECRET_KEY` « par défaut » oubliée en
production laisse n'importe qui forger des jetons.

```python
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY manquante : refus de démarrer.")
```

Générer la clé avec `secrets.token_urlsafe(32)`, jamais à la main.

## Secrets applicatifs — HashiCorp Vault

Même principe de fail-closed appliqué au gestionnaire de secrets lui-même :
sans connexion à Vault, l'application refuse de démarrer plutôt que de se
rabattre sur une valeur par défaut ou un secret laissé en dur.

```python
VAULT_ADDR = os.environ.get("VAULT_ADDR")
VAULT_TOKEN = os.environ.get("VAULT_TOKEN")
if not VAULT_ADDR or not VAULT_TOKEN:
    raise RuntimeError("Configuration Vault manquante : refus de démarrer.")
```

- **Jamais de jeton en dur dans le code**, y compris un jeton racine — le
  code reste agnostique et ne consomme que des variables d'environnement
  injectées par l'infrastructure. `os.environ["VAULT_TOKEN"] = "hvs...."`
  écrit dans le code est une facilité de développement local, jamais un
  patron de production.
- **AppRole pour l'authentification service à service** (M2M) : `role_id`
  connu de l'application, `secret_id` à usage unique et de courte durée
  (`secret_id_num_uses=1`, `secret_id_ttl="10m"`), restreint par CIDR
  (`secret_id_bound_cidrs=[...]`), et attaché à une politique nommée pour ce
  service précis (`token_policies=[...]`) — jamais la politique `default`.
- **KV v2** : `cas_required=True` sur le moteur force le verrouillage
  optimiste — une écriture qui ne connaît pas la version courante (ou passe
  `cas=0` alors que le secret existe déjà) lève
  `hvac.exceptions.InvalidRequest` plutôt que d'écraser silencieusement. Le
  nom d'un chemin ou d'une clé n'est **jamais filtré par la politique lors
  d'un `list`** : n'y encoder aucune information sensible (nom de client,
  incident en cours).
- **Un secret statique lu (KV) n'est pas révocable comme un secret
  dynamique.** Révoquer le bail attaché à une lecture KV ne coupe rien à un
  client qui a déjà récupéré la valeur — c'est une photocopie. Un secret
  dynamique (identifiants de base générés à la demande) l'est vraiment :
  Vault se connecte au système cible et supprime le compte. Ne pas compter
  sur une « révocation » de secret statique sans rotation manuelle côté
  système cible, suivie d'une réécriture dans Vault.
- **Moteur Transit** (chiffrement en tant que service) comme alternative à
  `cryptography.Fernet`/RSA (§ Chiffrement des données) quand Vault est déjà
  le gestionnaire de secrets du projet : l'application envoie/reçoit du texte
  encodé en base64 sans jamais manipuler de clé — le base64 est une exigence
  de transport, pas une mesure de sécurité en soi.
- **Response wrapping** pour la remise d'un secret une seule fois (mot de
  passe initial d'un compte admin, par exemple) : `client.sys.wrap(...)`
  produit un jeton cubbyhole à usage unique. Un deuxième `unwrap` qui échoue
  n'est pas une erreur à ignorer — c'est un signal qu'un tiers a intercepté
  et déjà consommé le jeton, à traiter comme un incident.

## Durcissement

- **Rate limiting** sur `/token` (`slowapi`, par IP) : c'est la seule défense
  contre le forçage de mots de passe. `/refresh` mérite le même traitement.
  La route décorée par `@limiter.limit(...)` doit déclarer `request: Request`
  parmi ses paramètres — sans lui, `slowapi` échoue à l'exécution, pas au
  démarrage.
- **CORS restreint** aux origines réellement attendues. `allow_origins=["*"]`
  avec `allow_credentials=True` est refusé par la spécification et par les
  navigateurs — la combinaison ne « marche » jamais, elle échoue silencieusement.
- **Anti-énumération** : message identique pour « compte inconnu » et « mot de
  passe incorrect », et vérifier un hash dans les deux cas pour lisser le temps
  de réponse. Sinon la durée de la réponse trahit l'existence du compte.
- HTTPS obligatoire : sans lui le Bearer circule en clair et tout le reste est
  sans objet.
- Stockage du jeton côté navigateur : cookie `httpOnly` + `SameSite` + jeton
  anti-CSRF plutôt que `localStorage`, qu'un XSS lit directement. Il n'y a pas
  de bonne réponse, seulement un arbitrage à écrire dans le `CLAUDE.md` du dépôt.

## Endpoint qui sert un modèle

Une prédiction coûte du calcul et le modèle a de la valeur : un jeton valide ne
suffit pas.

- **Validation métier stricte** avec Pydantic : des bornes réalistes
  (`Field(gt=0, le=12)`), pas seulement `ge=0`. Une entrée aberrante doit être
  rejetée en 422 avant d'atteindre le modèle.
- **Quota par utilisateur**, distinct du rate limiting par IP : il maîtrise le
  coût et freine l'extraction du modèle par interrogation massive. Dépassement
  → 429.
- Journaliser les accès refusés, et renvoyer la confiance en plus de la classe
  prédite.

## Si le modèle servi est un LLM

- Ne jamais concaténer aveuglément consigne système et entrée utilisateur :
  l'utilisateur peut écraser les instructions.
- Borner la sortie (longueur, format) et **ne jamais exécuter ni évaluer** ce que
  renvoie le modèle.
- Limiter les données sensibles accessibles au modèle.

L'injection de prompt n'a pas de correctif unique : c'est de la défense en
profondeur, à traiter comme un risque accepté et borné, pas comme un bug à
fermer. Implémentation (taxonomie d'attaque, quatre niveaux de défense,
guardrail structuré) dans `rules/agents-ia.md` § Sécurité — injection de
prompt.

## Réponses d'erreur

Le message d'une exception ne sort jamais vers le client. `rules/python.md`
fait remonter les exceptions jusqu'au point d'entrée, qui décide de l'affichage :
sur une route, décider signifie journaliser la trace complète et renvoyer un
message générique. Un `detail=str(e)` recopié tel quel trahit l'existence d'un
compte, un chemin de fichier ou l'URL de base avec son mot de passe.

## Journalisation

Ne jamais journaliser un mot de passe, un jeton, une clé — y compris en cas
d'échec d'authentification, où le réflexe de « logger l'entrée pour comprendre »
est le plus fort.
